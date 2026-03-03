"""
Aggregate metrics by grade, by company, and ten-rate.

Uses total_price_usd when set, else total_price. Bucketing follows backend/docs/BUCKETING.md.
"""

from typing import Optional, List

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Sale, CardIdentity, Set
from app.schemas.metrics import (
    ByCompanyResponse,
    ByGradeResponse,
    CompanyBucket,
    CompanyGradeBucket,
    GradeBucket,
    MetricsSummaryResponse,
    TenRateResponse,
    MoverCard,
    MoversResponseBase,
)

router = APIRouter()

# Use USD when available for cross-currency consistency
_PRICE_USD = func.coalesce(Sale.total_price_usd, Sale.total_price)


def _median_price_expr():
    return func.percentile_cont(0.5).within_group(_PRICE_USD)


@router.get("/summary", response_model=MetricsSummaryResponse)
def metrics_summary(db: Session = Depends(get_db)):
    """Total sales, counts by language, and raw vs graded."""
    total = db.execute(select(func.count(Sale.id))).scalars().first() or 0
    by_lang = (
        db.execute(
            select(Sale.language, func.count(Sale.id))
            .where(Sale.language.isnot(None))
            .group_by(Sale.language)
        )
        .all()
    )
    raw_count = db.execute(
        select(func.count(Sale.id)).where(Sale.grade_company.is_(None))
    ).scalars().first() or 0
    graded_count = db.execute(
        select(func.count(Sale.id)).where(Sale.grade_company.isnot(None))
    ).scalars().first() or 0
    return MetricsSummaryResponse(
        total_sales=total,
        by_language={str(k): v for k, v in by_lang},
        raw_count=raw_count,
        graded_count=graded_count,
    )


@router.get("/by-grade", response_model=ByGradeResponse)
def metrics_by_grade(
    language: Optional[str] = Query(None, description="Filter: en, jp, or other"),
    db: Session = Depends(get_db),
):
    """Aggregate by grade: count and median price per grade (and raw)."""
    base = select(
        Sale.grade_value,
        func.count(Sale.id).label("count"),
        _median_price_expr().label("median_price_usd"),
    )
    if language:
        base = base.where(Sale.language == language)
    base = base.group_by(Sale.grade_value)
    rows = db.execute(base).all()

    buckets = []
    for grade_value, count, median_price_usd in rows:
        if grade_value is None:
            label = "raw"
        else:
            label = str(int(grade_value)) if grade_value == int(grade_value) else str(grade_value)
        buckets.append(
            GradeBucket(
                grade_label=label,
                count=count,
                median_price_usd=round(median_price_usd, 2) if median_price_usd is not None else None,
            )
        )
    # Sort: raw first, then 10, 9.5, 9, ...
    def _sort_key(b: GradeBucket):
        if b.grade_label == "raw":
            return -1, 0
        try:
            return 0, float(b.grade_label)
        except ValueError:
            return 0, 0

    buckets.sort(key=_sort_key, reverse=True)
    return ByGradeResponse(buckets=buckets, language_filter=language)


@router.get("/by-company", response_model=ByCompanyResponse)
def metrics_by_company(
    language: Optional[str] = Query(None, description="Filter: en, jp, or other"),
    db: Session = Depends(get_db),
):
    """Aggregate by grading company with per-grade breakdown."""
    base_company = select(
        Sale.grade_company,
        func.count(Sale.id).label("count"),
        _median_price_expr().label("median_price_usd"),
    ).where(Sale.grade_company.isnot(None))
    if language:
        base_company = base_company.where(Sale.language == language)
    base_company = base_company.group_by(Sale.grade_company)
    company_rows = db.execute(base_company).all()

    base_breakdown = select(
        Sale.grade_company,
        Sale.grade_value,
        func.count(Sale.id).label("count"),
        _median_price_expr().label("median_price_usd"),
    ).where(Sale.grade_company.isnot(None))
    if language:
        base_breakdown = base_breakdown.where(Sale.language == language)
    base_breakdown = base_breakdown.group_by(Sale.grade_company, Sale.grade_value)
    breakdown_rows = db.execute(base_breakdown).all()

    breakdown_by_company: dict = {}
    for company, grade_value, count, median in breakdown_rows:
        company = str(company)
        if company not in breakdown_by_company:
            breakdown_by_company[company] = []
        breakdown_by_company[company].append(
            CompanyGradeBucket(
                grade_value=float(grade_value) if grade_value is not None else None,
                count=count,
                median_price_usd=round(median, 2) if median is not None else None,
            )
        )
    for lst in breakdown_by_company.values():
        lst.sort(key=lambda x: (x.grade_value or 0), reverse=True)

    buckets = []
    for company, count, median_price_usd in company_rows:
        company = str(company)
        buckets.append(
            CompanyBucket(
                company=company,
                count=count,
                median_price_usd=round(median_price_usd, 2) if median_price_usd is not None else None,
                grade_breakdown=breakdown_by_company.get(company, []),
            )
        )
    buckets.sort(key=lambda b: b.count, reverse=True)
    return ByCompanyResponse(buckets=buckets, language_filter=language)


@router.get("/ten-rate", response_model=TenRateResponse)
def metrics_ten_rate(
    language: Optional[str] = Query(None, description="Filter: en, jp, or other"),
    db: Session = Depends(get_db),
):
    """Fraction of graded sales that are grade 10 (overall and per company)."""
    base = select(
        Sale.grade_company,
        func.count(Sale.id).label("total"),
        func.sum(case((Sale.grade_value >= 9.99, 1), else_=0)).label("tens"),
    ).where(Sale.grade_company.isnot(None))
    if language:
        base = base.where(Sale.language == language)
    base = base.group_by(Sale.grade_company)
    rows = db.execute(base).all()

    graded_count = 0
    ten_count = 0
    by_company = {}
    for company, total, tens in rows:
        total = total or 0
        tens = tens or 0
        graded_count += total
        ten_count += tens
        by_company[str(company)] = round(tens / total, 4) if total else 0.0

    overall = round(ten_count / graded_count, 4) if graded_count else None
    return TenRateResponse(
        overall_ten_rate=overall,
        graded_count=graded_count,
        ten_count=ten_count,
        by_company=by_company,
    )


@router.get("/movers", response_model=MoversResponseBase)
def metrics_movers(
    window_days: int = Query(30, ge=7, le=180, description="Window in days for recent price"),
    min_sales_now: int = Query(3, ge=1, description="Minimum raw sales in the recent window"),
    min_sales_prev: int = Query(3, ge=0, description="Minimum raw sales in the previous window"),
    limit: int = Query(50, ge=1, le=200, description="Maximum cards to return"),
    language: Optional[str] = Query(None, description="Optional language filter: en, jp, other"),
    db: Session = Depends(get_db),
):
    """
    Top movers across all cards (PriceCharting-style).

    For each card_id:
    - value_now = median raw price over last `window_days`
    - value_prev = median raw price over the preceding `window_days`
    - change_pct = (value_now - value_prev) / value_prev
    """
    # Pull ungraded sales that have card_id and sold_at; we will filter by time in pandas.
    base = select(Sale).where(
        Sale.grade_company.is_(None),
        Sale.card_id.isnot(None),
        Sale.sold_at.isnot(None),
    )
    if language:
        base = base.where(Sale.language == language)
    rows = db.execute(base).scalars().all()

    if not rows:
        return MoversResponseBase(window_days=window_days, min_sales_now=min_sales_now, min_sales_prev=min_sales_prev, cards=[])

    # Convert to DataFrame for grouping.
    data = []
    # We'll approximate "now" using the max sold_at in data since func.now() doesn't exist in Python.
    for s in rows:
        if not s.sold_at:
            continue
        data.append(
            {
                "card_id": str(s.card_id),
                "sold_at": s.sold_at,
                "price": float(s.total_price_usd or s.total_price),
            }
        )
    if not data:
        return MoversResponseBase(window_days=window_days, min_sales_now=min_sales_now, min_sales_prev=min_sales_prev, cards=[])

    df = pd.DataFrame(data)
    cutoff_max = df["sold_at"].max()
    recent_start = cutoff_max - pd.Timedelta(days=window_days)
    prev_start = recent_start - pd.Timedelta(days=window_days)

    movers: List[MoverCard] = []
    for card_id, group in df.groupby("card_id"):
        recent_mask = group["sold_at"] > recent_start
        prev_mask = (group["sold_at"] > prev_start) & (group["sold_at"] <= recent_start)
        recent = group[recent_mask]
        prev = group[prev_mask]
        sales_now = len(recent)
        sales_prev = len(prev)
        if sales_now < min_sales_now or sales_prev < min_sales_prev:
            continue
        value_now = float(recent["price"].median()) if not recent.empty else None
        value_prev = float(prev["price"].median()) if not prev.empty else None
        if not value_prev or value_prev <= 0 or value_now is None:
            continue
        change_pct = (value_now - value_prev) / value_prev
        movers.append(
            MoverCard(
                card_id=card_id,
                name=card_id,  # will be filled from CardIdentity below
                set_slug=None,
                set_name=None,
                window_days=window_days,
                value_now_usd=round(value_now, 2),
                value_prev_usd=round(value_prev, 2),
                change_pct=change_pct,
                sales_now=sales_now,
                sales_prev=sales_prev,
            )
        )

    if not movers:
        return MoversResponseBase(window_days=window_days, min_sales_now=min_sales_now, min_sales_prev=min_sales_prev, cards=[])

    # Attach canonical names and set info where available.
    ids = [m.card_id for m in movers]
    ident_rows = (
        db.execute(select(CardIdentity, Set).join(Set, CardIdentity.set_id == Set.id, isouter=True).where(CardIdentity.card_id.in_(ids)))
        .all()
    )
    ident_by_id = {}
    for ident, s in ident_rows:
        ident_by_id[str(ident.card_id)] = (ident, s)

    for m in movers:
        ident_s = ident_by_id.get(m.card_id)
        if ident_s:
            ident, s = ident_s
            m.name = ident.name or m.name
            m.set_slug = s.set_slug if s else None
            m.set_name = s.set_name if s else ident.set_name

    # Sort by absolute change descending (biggest movers), then by sales_now as tiebreaker.
    movers.sort(key=lambda m: (abs(m.change_pct or 0.0), m.sales_now), reverse=True)
    return MoversResponseBase(
        window_days=window_days,
        min_sales_now=min_sales_now,
        min_sales_prev=min_sales_prev,
        cards=movers[:limit],
    )
