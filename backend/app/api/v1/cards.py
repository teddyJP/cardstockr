from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import CardIdentity, Sale, Set
from app.schemas.cards import (
    CardSearchResult,
    CardDetail,
    CardTimeSeriesPoint,
    CardForecastPoint,
    PriceByGrade,
    GradeCount,
    CompanyGradeDistribution,
    GradingUpside,
    CardSeriesLine,
    CardSeriesPoint,
    CardSeriesResponse,
)
from app.services.card_image import resolve_card_image
from app.services.title_parser import parse_card_name, parse_card_number, parse_set_from_title

router = APIRouter()

DEFAULT_GRADING_COST_USD = 25.0


def _price_usd(s: Sale) -> float:
    return float(s.total_price_usd if s.total_price_usd is not None else s.total_price)


def _bucket_key(s: Sale) -> Tuple[Optional[str], Optional[float]]:
    return (getattr(s, "grade_company", None), getattr(s, "grade_value", None))


def _normalize_condition(cond: Optional[str]) -> str:
    """
    Map free-text condition into coarse buckets:
    Damaged, HP, MP, LP, NM, Unknown.
    """
    if not cond:
        return "Unknown"
    c = cond.lower()
    if "damaged" in c or "poor" in c:
        return "Damaged"
    if "heav" in c or "hp" in c:
        return "HP"
    if "mod" in c or "mp" in c:
        return "MP"
    if "light" in c or "lp" in c:
        return "LP"
    if "near mint" in c or "nm" in c:
        return "NM"
    return "Unknown"

def _resolve_sales(raw: str, db: Session) -> Tuple[str, Optional[str], List[Sale]]:
    """
    Resolve sales for a card identifier:
    - If raw contains '/', treat as canonical Sale.card_id
    - Else treat as legacy listing title
    Returns (display_title, canonical_card_id, sales)
    """
    raw = (raw or "").strip()
    title = raw
    canonical = None
    sales: List[Sale] = []

    if "/" in raw:
        canonical = raw
        stmt = select(Sale).where(Sale.card_id == raw).order_by(Sale.sold_at.asc())
        sales = db.execute(stmt).scalars().all()
        if sales:
            title = sales[0].title
        return title, canonical, sales

    # exact title
    stmt = select(Sale).where(Sale.title == raw).order_by(Sale.sold_at.asc())
    sales = db.execute(stmt).scalars().all()
    if sales:
        canonical = sales[0].card_id if sales[0].card_id and "/" in str(sales[0].card_id) else None
        return raw, canonical, sales

    # trimmed match
    stmt = select(Sale).where(func.trim(Sale.title) == raw).order_by(Sale.sold_at.asc())
    sales = db.execute(stmt).scalars().all()
    if sales:
        title = sales[0].title
        canonical = sales[0].card_id if sales[0].card_id and "/" in str(sales[0].card_id) else None
        return title, canonical, sales

    # ilike fallback
    stmt = select(Sale).where(Sale.title.ilike(f"%{raw}%")).order_by(Sale.sold_at.asc())
    found = db.execute(stmt).scalars().all()
    if found:
        first_title = found[0].title
        sales = [s for s in found if s.title == first_title]
        canonical = sales[0].card_id if sales and sales[0].card_id and "/" in str(sales[0].card_id) else None
        return first_title, canonical, sales

    return title, canonical, []


@router.get("/search", response_model=List[CardSearchResult])
def search_cards(
    q: str = Query(..., min_length=1, description="Card title or partial"),
    language: Optional[str] = Query(None, description="Optional language filter: en, jp, other"),
    db: Session = Depends(get_db),
):
    """
    Search for cards, returning one row per canonical card (like PriceCharting).

    Primary source is CardIdentity (one row per card). If no identities match
    (e.g. before backfill), we fall back to aggregating sales titles.
    """
    pattern = f"%{q}%"

    results: List[CardSearchResult] = []

    # 1) Preferred: query canonical CardIdentity rows (one per actual card).
    ident_stmt = (
        select(
            CardIdentity.card_id,
            CardIdentity.name,
            CardIdentity.number,
            CardIdentity.variant,
            Set.set_name,
            Set.set_slug,
            CardIdentity.image_url,
        )
        .join(Set, CardIdentity.set_id == Set.id, isouter=True)
        .where(
            (CardIdentity.name.ilike(pattern))
            | (CardIdentity.number.ilike(pattern))
            | (Set.set_name.ilike(pattern))
        )
        .order_by(Set.set_name.asc().nulls_last(), CardIdentity.name.asc())
        .limit(50)
    )
    ident_rows = db.execute(ident_stmt).all()
    for cid, name, number, variant, set_name, set_slug, image_url in ident_rows:
        results.append(
            CardSearchResult(
                card_id=str(cid),
                name=name or "",
                set_name=set_name or "Unknown",
                year=0,
                number=number or "-",
                variant=variant,
                set_slug=set_slug,
                image_url=image_url,
                grade_company=None,
                grade_value=None,
            )
        )

    # 2) Fallback: search raw titles and aggregate into card-like identities.
    stmt = select(Sale.title, Sale.card_id).where(Sale.title.ilike(pattern))
    if language:
        stmt = stmt.where(Sale.language == language)
    stmt = stmt.limit(200)
    rows = db.execute(stmt).all()

    # key: (card_name, set_name, card_number) -> canonical_card_id
    by_key: dict = {}
    for title, cid in rows:
        name = parse_card_name(title or "")
        set_name = parse_set_from_title(title or "")
        number = parse_card_number(title or "")
        key = (name, set_name, number or "-")
        # Prefer canonical card_id with set_slug/card_slug when present
        if key not in by_key or (cid and "/" in str(cid or "")):
            by_key[key] = cid

    for (name, set_name, number), cid in list(by_key.items())[:25]:
        results.append(
            CardSearchResult(
                card_id=(cid if cid and "/" in str(cid) else name),
                name=name,
                set_name=set_name or "Unknown",
                year=0,
                number=number or "-",
                set_slug=str(cid).split("/", 1)[0] if cid and "/" in str(cid) else None,
                grade_company=None,
                grade_value=None,
            )
        )

    # Attach simple raw price summary per card (PriceCharting-style).
    canonical_ids = [r.card_id for r in results if "/" in r.card_id][:50]
    if canonical_ids:
        sales_stmt = select(Sale).where(Sale.card_id.in_(canonical_ids))
        if language:
            sales_stmt = sales_stmt.where(Sale.language == language)
        sales_rows = db.execute(sales_stmt).scalars().all()
        raw_by_card: dict = defaultdict(list)
        for s in sales_rows:
            if s.grade_company is None:
                raw_by_card[str(s.card_id)].append(_price_usd(s))
        for r in results:
            prices = raw_by_card.get(r.card_id) or []
            if prices:
                s = pd.Series(prices)
                r.raw_sales_count = len(prices)
                r.raw_median_usd = round(float(s.median()), 2)
                # Low/mid/high band similar to PriceCharting style
                r.raw_low_usd = round(float(s.quantile(0.1)), 2)
                r.raw_high_usd = round(float(s.quantile(0.9)), 2)

    return results[:25]


@router.get("/{card_id}", response_model=CardDetail)
def get_card_detail(card_id: str, db: Session = Depends(get_db)):
    """
    Detail view for a card. Supports:
    - Canonical id: set_slug/card_slug (e.g. ascended-heroes/mega-gengar-ex-284) when sales have been backfilled.
    - Legacy: full listing title string from search.
    """
    title, canonical_card_id, sales = _resolve_sales(card_id, db)

    if not sales:
        raise HTTPException(status_code=404, detail="No sales found for this card")

    # Resolve set/card info
    set_name = None
    set_slug = None
    card_slug = None
    number = "-"
    display_name = title
    ident = None
    if canonical_card_id and "/" in canonical_card_id:
        set_slug, card_slug = canonical_card_id.split("/", 1)
        ident = db.execute(select(CardIdentity).where(CardIdentity.card_id == canonical_card_id)).scalars().first()
        if ident and ident.set_id:
            s = db.execute(select(Set).where(Set.id == ident.set_id)).scalars().first()
            if s:
                set_name = s.set_name
        if ident:
            display_name = ident.name or title
            number = ident.number or number
    if not set_name:
        set_name = parse_set_from_title(title)
    if display_name == title:
        # Use sale parsed fields if present
        if sales and sales[0].player_or_pokemon_name:
            display_name = sales[0].player_or_pokemon_name
        if sales and sales[0].card_number:
            number = sales[0].card_number

    # --- PriceCharting-style: prices by grade, grade distribution, grading upside ---
    by_bucket: dict = defaultdict(list)
    for s in sales:
        by_bucket[_bucket_key(s)].append(_price_usd(s))

    prices_by_grade: List[PriceByGrade] = []
    for (company, gv), prices in sorted(by_bucket.items(), key=lambda x: (x[0][0] or "", x[0][1] or 0), reverse=True):
        if company is None and gv is None:
            label = "Ungraded"
        else:
            label = f"{company} {int(gv) if gv == int(gv) else gv}"
        median_p = float(pd.Series(prices).median())
        prices_by_grade.append(
            PriceByGrade(
                label=label,
                grade_company=company,
                grade_value=gv,
                median_price_usd=round(median_p, 2),
                count=len(prices),
            )
        )
    # Sort: Ungraded first, then by company name, then grade desc
    def _pbg_sort(p: PriceByGrade):
        if p.grade_company is None:
            return (0, "", 0.0)
        return (1, p.grade_company or "", -(p.grade_value or 0))
    prices_by_grade.sort(key=_pbg_sort)

    # Grade distribution per company (sales count per grade)
    by_company_grade: dict = defaultdict(lambda: defaultdict(list))
    for s in sales:
        if s.grade_company is None:
            continue
        by_company_grade[s.grade_company][s.grade_value].append(_price_usd(s))
    grade_distribution: List[CompanyGradeDistribution] = []
    graded_price_bands: List[CompanyPriceBand] = []
    for company in sorted(by_company_grade.keys()):
        grades = by_company_grade[company]
        total_graded = sum(len(prices) for prices in grades.values())
        by_grade = [GradeCount(grade_value=gv, count=len(prices)) for gv, prices in sorted(grades.items(), reverse=True)]
        ten_count = sum(len(prices) for gv, prices in grades.items() if gv is not None and gv >= 9.99)
        ten_rate = round(ten_count / total_graded, 4) if total_graded else None
        grade_distribution.append(
            CompanyGradeDistribution(company=company, total_graded=total_graded, by_grade=by_grade, ten_rate=ten_rate)
        )
        # Price band for this company's graded prices
        all_prices: list[float] = []
        for _, prices in grades.items():
            all_prices.extend(prices)
        if all_prices:
            s = pd.Series(all_prices)
            low = float(s.quantile(0.1))
            med = float(s.median())
            high = float(s.quantile(0.9))
            graded_price_bands.append(
                CompanyPriceBand(
                    company=company,
                    low_usd=round(low, 2),
                    median_usd=round(med, 2),
                    high_usd=round(high, 2),
                    sales_count=len(all_prices),
                )
            )

    # Grading upside: EV per company vs raw + raw value band
    raw_prices = by_bucket.get((None, None), [])
    raw_series = pd.Series(raw_prices) if raw_prices else None
    raw_median = float(raw_series.median()) if raw_series is not None and not raw_series.empty else 0.0
    by_company_upside: List[dict] = []
    for company in sorted(by_company_grade.keys()):
        grades = by_company_grade[company]
        total = sum(len(p) for p in grades.values())
        if total == 0:
            continue
        ev = 0.0
        for gv, prices in grades.items():
            p_g = len(prices) / total
            med = float(pd.Series(prices).median())
            ev += p_g * med
        upside = ev - raw_median - DEFAULT_GRADING_COST_USD
        by_company_upside.append({
            "company": company,
            "ev_usd": round(ev, 2),
            "upside_usd": round(upside, 2),
            "worth_grading": upside > 0,
        })
    grading_upside = GradingUpside(
        raw_median_usd=round(raw_median, 2),
        grading_cost_usd=DEFAULT_GRADING_COST_USD,
        by_company=by_company_upside,
        worth_grading_any=any(x["worth_grading"] for x in by_company_upside),
    ) if (raw_prices and by_company_upside) else None

    # Raw-by-condition buckets (using only ungraded sales).
    raw_by_condition_prices: dict = defaultdict(list)
    for s in sales:
        if s.grade_company is None:
            bucket = _normalize_condition(getattr(s, "condition_raw", None))
            raw_by_condition_prices[bucket].append(_price_usd(s))

    raw_by_condition: dict = {}
    for bucket, prices in raw_by_condition_prices.items():
        if not prices:
            continue
        med = float(pd.Series(prices).median())
        raw_by_condition[bucket] = {
            "median_price_usd": round(med, 2),
            "count": len(prices),
        }

    # Recent-window aggregates (e.g. last 90 days) per condition and per grade.
    recent_window_days = 90
    recent_cutoff = None
    # Use most recent sold_at among all sales with a timestamp.
    dated_sales = [s for s in sales if isinstance(s.sold_at, datetime)]
    if dated_sales:
        recent_cutoff = max(s.sold_at for s in dated_sales) - timedelta(days=recent_window_days)

    recent_raw_by_condition: dict = {}
    if recent_cutoff is not None:
        recent_raw_prices: dict = defaultdict(list)
        for s in dated_sales:
            if s.grade_company is None and s.sold_at >= recent_cutoff:
                bucket = _normalize_condition(getattr(s, "condition_raw", None))
                recent_raw_prices[bucket].append(_price_usd(s))
        for bucket, prices in recent_raw_prices.items():
            if not prices:
                continue
            series = pd.Series(prices)
            med = float(series.median())
            recent_raw_by_condition[bucket] = {
                "median_price_usd": round(med, 2),
                "count": len(prices),
            }

    recent_prices_by_grade: List[PriceByGrade] = []
    if recent_cutoff is not None:
        recent_bucket: dict = defaultdict(list)
        for s in dated_sales:
            if s.sold_at >= recent_cutoff:
                recent_bucket[_bucket_key(s)].append(_price_usd(s))
        for (company, gv), prices in sorted(
            recent_bucket.items(), key=lambda x: (x[0][0] or "", x[0][1] or 0), reverse=True
        ):
            if not prices:
                continue
            if company is None and gv is None:
                label = "Ungraded"
            else:
                label = f"{company} {int(gv) if gv == int(gv) else gv}"
            median_p = float(pd.Series(prices).median())
            recent_prices_by_grade.append(
                PriceByGrade(
                    label=label,
                    grade_company=company,
                    grade_value=gv,
                    median_price_usd=round(median_p, 2),
                    count=len(prices),
                )
            )
        def _pbg_sort_recent(p: PriceByGrade):
            if p.grade_company is None:
                return (0, "", 0.0)
            return (1, p.grade_company or "", -(p.grade_value or 0))
        recent_prices_by_grade.sort(key=_pbg_sort_recent)

    # Build a time series of USD-normalized price by sold_at.
    data = [
        {
            "sold_at": s.sold_at,
            "total_price": _price_usd(s),
        }
        for s in sales
        if isinstance(s.sold_at, datetime)
    ]

    if not data:
        raise HTTPException(status_code=404, detail="No dated sales found for this card")

    df = pd.DataFrame(data)
    df = df.sort_values("sold_at").set_index("sold_at")

    # Resample to daily median price and count of sales per day.
    daily = df.resample("D").agg(
        median_price=("total_price", "median"),
        sales_count=("total_price", "count"),
    )
    daily = daily.dropna(subset=["median_price"])

    history: List[CardTimeSeriesPoint] = [
        CardTimeSeriesPoint(
            date=idx.date(),
            median_price=float(row.median_price),
            sales_count=int(row.sales_count),
        )
        for idx, row in daily.iterrows()
    ]

    # Fair value now: median of last 14 days (or all if fewer).
    if not daily.empty:
        recent_window = daily.tail(14)
        fair_value_now = float(recent_window["median_price"].median())
    else:
        fair_value_now = float(df["total_price"].median())

    # Simple uncertainty band: ±15% around fair value for now.
    fair_value_ci_low = fair_value_now * 0.85
    fair_value_ci_high = fair_value_now * 1.15

    # Risk score: based on price volatility (std dev of log returns) scaled 0–100.
    prices = df["total_price"].sort_index()
    returns = prices.pct_change().dropna()
    if len(returns) >= 3:
        vol = float(returns.std())
        risk_score = max(0, min(100, int(vol * 400)))  # heuristic scaling
    else:
        risk_score = 20

    # Liquidity score: based on number of sales and recency.
    total_sales = len(sales)
    days_span = (sales[-1].sold_at.date() - sales[0].sold_at.date()).days or 1
    sales_per_week = (total_sales / days_span) * 7.0
    liquidity_score = max(0, min(100, int(sales_per_week * 20)))  # 5+/week ~ 100

    # 30d / 90d trend: median in recent window vs previous window
    change_30d_pct_val: Optional[float] = None
    change_90d_pct_val: Optional[float] = None
    if not daily.empty:
        cutoff = daily.index.max()
        for window_days in [30, 90]:
            recent = daily[daily.index > (cutoff - pd.Timedelta(days=window_days))]
            prev = daily[(daily.index <= (cutoff - pd.Timedelta(days=window_days))) & (daily.index > cutoff - pd.Timedelta(days=2 * window_days))]
            if not recent.empty and not prev.empty:
                med_now = float(recent["median_price"].median())
                med_prev = float(prev["median_price"].median())
                if med_prev and med_prev > 0:
                    pct = round((med_now - med_prev) / med_prev, 4)
                    if window_days == 30:
                        change_30d_pct_val = pct
                    else:
                        change_90d_pct_val = pct

    # Simple trend-based forecast on daily medians for next 30 days.
    # Uses a linear fit over the last ~60 days of daily median prices and derives an uncertainty band from residuals.
    forecast: List[CardForecastPoint] = []
    forecast_horizon_days: int = 0
    if not daily.empty and fair_value_now > 0:
        # Use up to last 60 days of daily medians for the trend fit.
        history_window = daily.tail(60)
        if len(history_window) >= 5:
            import numpy as np

            y = history_window["median_price"].astype(float).values
            t = np.arange(len(y), dtype=float)

            # Linear trend: y ≈ a * t + b
            a, b = np.polyfit(t, y, 1)
            y_hat = a * t + b
            resid = y - y_hat
            sigma = float(np.std(resid)) if len(resid) > 1 else 0.0

            last_idx = daily.index.max()
            last_date = last_idx.date() if hasattr(last_idx, "date") else last_idx

            horizon = 30
            for d in range(1, horizon + 1):
                t_future = len(y) - 1 + d
                base = float(a * t_future + b)
                # Fall back to fair_value_now if regression gives non-positive.
                base = base if base > 0 else fair_value_now
                # Approximate 10th/90th percentiles assuming normal-ish residuals.
                band = 1.28 * sigma if sigma > 0 else fair_value_now * 0.15
                p50 = base
                p10 = max(0.01, p50 - band)
                p90 = p50 + band

                fd = last_date + timedelta(days=d)
                forecast.append(
                    CardForecastPoint(
                        date=fd,
                        p10=round(p10, 2),
                        p50=round(p50, 2),
                        p90=round(p90, 2),
                    )
                )
            forecast_horizon_days = horizon

    # Raw value band across all ungraded sales
    raw_low = float(raw_series.quantile(0.1)) if raw_series is not None and not raw_series.empty else None
    raw_high = float(raw_series.quantile(0.9)) if raw_series is not None and not raw_series.empty else None
    raw_sales_count = len(raw_prices)

    image_url = (getattr(ident, "image_url", None) if ident else None) or resolve_card_image(set_name, number or "-")

    return CardDetail(
        card_id=canonical_card_id or title,
        canonical_card_id=canonical_card_id,
        set_slug=set_slug,
        card_slug=card_slug,
        image_url=image_url,
        name=display_name,
        set_name=set_name or "Unknown",
        year=0,
        number=number or "-",
        grade_company=None,
        grade_value=None,
        fair_value_now=fair_value_now,
        fair_value_ci_low=fair_value_ci_low,
        fair_value_ci_high=fair_value_ci_high,
        forecast_horizon_days=forecast_horizon_days,
        liquidity_score=liquidity_score,
        risk_score=risk_score,
        change_30d_pct=change_30d_pct_val,
        change_90d_pct=change_90d_pct_val,
        recent_window_days=recent_window_days,
        raw_low_usd=round(raw_low, 2) if raw_low is not None else None,
        raw_median_usd=round(raw_median, 2) if raw_prices else None,
        raw_high_usd=round(raw_high, 2) if raw_high is not None else None,
        raw_sales_count=raw_sales_count,
        history=history,
        forecast=forecast,
        prices_by_grade=prices_by_grade,
        grade_distribution=grade_distribution,
        grading_upside=grading_upside,
        graded_price_bands=graded_price_bands,
        raw_by_condition=raw_by_condition,
        recent_raw_by_condition=recent_raw_by_condition,
        recent_prices_by_grade=recent_prices_by_grade,
        recent_sales=[
            {
                "sold_at": s.sold_at.isoformat() if s.sold_at else None,
                "price_usd": round(_price_usd(s), 2),
                "currency": s.currency,
                "grade_company": s.grade_company,
                "grade_value": s.grade_value,
                "condition": s.condition_raw,
                "title": s.title,
                "source": s.source,
            }
            for s in sorted(sales, key=lambda x: x.sold_at or datetime.min, reverse=True)[:25]
        ],
        last_updated=datetime.utcnow(),
    )


@router.get("/series", response_model=CardSeriesResponse)
def get_card_series(
    card_id: str = Query(..., description="Canonical set_slug/card_slug or legacy title"),
    companies: Optional[str] = Query(None, description="Comma-separated companies (e.g. PSA,BGS,CGC)"),
    grades: Optional[str] = Query(None, description="Comma-separated grade values (e.g. 10,9.5,9)"),
    include_raw: bool = Query(True),
    raw_conditions: Optional[str] = Query(None, description="Comma-separated raw conditions for separate lines (e.g. NM,LP)"),
    group_by: str = Query("company", pattern="^(company|combined)$"),
    db: Session = Depends(get_db),
):
    """
    Returns daily median series for selected company/grade filters.

    - Multiple companies supported (overlay lines).
    - If include_raw and raw_conditions is set, raw sales are split into lines per condition (e.g. Raw (NM), Raw (LP)).
    """
    title, canonical, sales = _resolve_sales(card_id, db)
    if not sales:
        raise HTTPException(status_code=404, detail="No sales found for this card")

    company_list = [c.strip().upper() for c in companies.split(",")] if companies else []
    grade_list: List[float] = []
    if grades:
        for g in grades.split(","):
            g = g.strip()
            if not g:
                continue
            try:
                grade_list.append(float(g))
            except ValueError:
                continue

    raw_condition_set: Optional[set] = None
    if raw_conditions:
        raw_condition_set = {c.strip() for c in raw_conditions.split(",") if c.strip()}

    rows = []
    for s in sales:
        is_raw = s.grade_company is None
        if is_raw and not include_raw:
            continue
        if is_raw:
            if raw_condition_set:
                bucket = _normalize_condition(getattr(s, "condition_raw", None))
                if bucket not in raw_condition_set:
                    continue
                rows.append(
                    {
                        "sold_at": s.sold_at,
                        "price": _price_usd(s),
                        "company": f"RAW ({bucket})",
                    }
                )
            else:
                rows.append(
                    {
                        "sold_at": s.sold_at,
                        "price": _price_usd(s),
                        "company": "RAW",
                    }
                )
            continue
        comp = (s.grade_company or "").upper()
        if company_list and comp not in company_list:
            continue
        if grade_list and (s.grade_value is None or float(s.grade_value) not in grade_list):
            continue
        rows.append(
            {
                "sold_at": s.sold_at,
                "price": _price_usd(s),
                "company": comp,
            }
        )

    if not rows:
        raise HTTPException(status_code=404, detail="No sales match the selected filters")

    df = pd.DataFrame(rows)
    df = df.sort_values("sold_at")
    df["day"] = pd.to_datetime(df["sold_at"]).dt.date

    series: List[CardSeriesLine] = []
    if group_by == "combined":
        daily = (
            df.groupby("day")["price"]
            .agg(median_price_usd="median", sales_count="count")
            .reset_index()
        )
        points = [
            CardSeriesPoint(
                date=row["day"],
                median_price_usd=float(row["median_price_usd"]),
                sales_count=int(row["sales_count"]),
            )
            for _, row in daily.iterrows()
        ]
        series = [CardSeriesLine(label="Selected", grade_company=None, points=points)]
    else:
        for comp, g in df.groupby("company"):
            daily = (
                g.groupby("day")["price"]
                .agg(median_price_usd="median", sales_count="count")
                .reset_index()
            )
            points = [
                CardSeriesPoint(
                    date=row["day"],
                    median_price_usd=float(row["median_price_usd"]),
                    sales_count=int(row["sales_count"]),
                )
                for _, row in daily.iterrows()
            ]
            if comp == "RAW":
                label = "Raw"
                grade_company = None
            elif comp.startswith("RAW ("):
                label = "Raw" + comp[3:]
                grade_company = None
            else:
                label = comp
                grade_company = comp
            series.append(
                CardSeriesLine(
                    label=label,
                    grade_company=grade_company,
                    points=points,
                )
            )

        # stable order: Raw lines first (alphabetically), then companies
        def _sort_key(line: CardSeriesLine):
            if line.label.startswith("Raw"):
                return (0, line.label)
            return (1, line.label)
        series.sort(key=_sort_key)

    return CardSeriesResponse(
        canonical_card_id=canonical,
        group_by=group_by,
        companies=company_list,
        grades=grade_list,
        include_raw=include_raw,
        series=series,
    )

