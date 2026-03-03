"""
Grading targets: rank cards by expected grading upside (PriceCharting++ feature).

This uses observed grade distributions from *sales* (not true population reports).
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import CardIdentity, Sale
from app.schemas.targets import GradingTarget, GradingTargetsResponse

router = APIRouter()

PRICE_USD = func.coalesce(Sale.total_price_usd, Sale.total_price)
MEDIAN_USD = func.percentile_cont(0.5).within_group(PRICE_USD)


@router.get("/grading", response_model=GradingTargetsResponse)
def grading_targets(
    limit: int = Query(50, ge=1, le=500),
    language: Optional[str] = Query(None, description="Filter: en, jp, other"),
    set_slug: Optional[str] = Query(None, description="Filter: only this set_slug"),
    grading_cost_usd: float = Query(25.0, ge=0),
    min_raw_sales: int = Query(2, ge=0),
    min_graded_sales: int = Query(2, ge=0),
    min_sales_per_week: float = Query(0.0, ge=0.0),
    max_volatility: Optional[float] = Query(None, ge=0.0, description="Max std-dev of returns (risk proxy)"),
    min_upside_usd: Optional[float] = Query(None, description="Only include cards with best_upside >= this"),
    db: Session = Depends(get_db),
):
    """
    Returns top cards ranked by best grading upside across companies:
    upside = EV(company) - raw_median - grading_cost.
    """
    # Base filter: use canonical card_id if present
    base_where = [Sale.card_id.isnot(None)]
    if language:
        base_where.append(Sale.language == language)
    if set_slug:
        base_where.append(Sale.card_id.ilike(f"{set_slug}/%"))

    # Raw medians per card_id
    raw_stmt = (
        select(
            Sale.card_id,
            func.count(Sale.id).label("raw_count"),
            MEDIAN_USD.label("raw_median"),
        )
        .where(*base_where)
        .where(Sale.grade_company.is_(None))
        .group_by(Sale.card_id)
    )
    raw_rows = db.execute(raw_stmt).all()
    raw_by_card: Dict[str, Tuple[int, float]] = {
        str(card_id): (int(cnt), float(med or 0.0)) for card_id, cnt, med in raw_rows
    }

    # Graded: median per (card_id, company, grade) and count
    graded_stmt = (
        select(
            Sale.card_id,
            Sale.grade_company,
            Sale.grade_value,
            func.count(Sale.id).label("cnt"),
            MEDIAN_USD.label("median"),
        )
        .where(*base_where)
        .where(Sale.grade_company.isnot(None))
        .group_by(Sale.card_id, Sale.grade_company, Sale.grade_value)
    )
    graded_rows = db.execute(graded_stmt).all()

    # Organize graded rows: card -> company -> grade -> (count, median)
    graded: Dict[str, Dict[str, Dict[float, Tuple[int, float]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    graded_count_by_card: Dict[str, int] = defaultdict(int)
    for card_id, company, grade_value, cnt, median in graded_rows:
        if not card_id or not company or grade_value is None:
            continue
        c = str(card_id)
        comp = str(company)
        gv = float(grade_value)
        graded[c][comp][gv] = (int(cnt), float(median or 0.0))
        graded_count_by_card[c] += int(cnt)

    # Pull names for cards (optional; if missing, use card_id)
    ids = list(set(list(raw_by_card.keys()) + list(graded_count_by_card.keys())))
    name_map: Dict[str, str] = {}
    if ids:
        rows = db.execute(select(CardIdentity.card_id, CardIdentity.name).where(CardIdentity.card_id.in_(ids))).all()
        for cid, nm in rows:
            name_map[str(cid)] = str(nm)

    # Liquidity: sales per week from total sales span
    liq_stmt = (
        select(
            Sale.card_id,
            func.count(Sale.id).label("total_sales"),
            func.min(Sale.sold_at).label("min_dt"),
            func.max(Sale.sold_at).label("max_dt"),
        )
        .where(*base_where)
        .group_by(Sale.card_id)
    )
    liq_rows = db.execute(liq_stmt).all()
    sales_per_week: Dict[str, float] = {}
    for card_id, total, min_dt, max_dt in liq_rows:
        if not card_id or not min_dt or not max_dt:
            continue
        days = max(1, (max_dt.date() - min_dt.date()).days)
        spw = (float(total) / float(days)) * 7.0
        sales_per_week[str(card_id)] = spw

    # Risk proxy: volatility of simple returns per card_id (std dev of pct-change across sales)
    # Uses a window LAG in Postgres; only computed for cards passing base filters.
    vol_by_card: Dict[str, float] = {}
    try:
        vol_sql = """
        WITH s AS (
          SELECT
            card_id,
            sold_at,
            COALESCE(total_price_usd, total_price) AS price,
            LAG(COALESCE(total_price_usd, total_price)) OVER (PARTITION BY card_id ORDER BY sold_at) AS prev
          FROM sales
          WHERE card_id IS NOT NULL
            AND (:language IS NULL OR language = :language)
            AND (:set_slug IS NULL OR card_id ILIKE (:set_slug || '/%'))
        )
        SELECT card_id, STDDEV_SAMP((price - prev) / NULLIF(prev, 0)) AS vol
        FROM s
        WHERE prev IS NOT NULL AND prev > 0 AND price > 0
        GROUP BY card_id
        """
        rows = db.execute(
            text(vol_sql),
            {"language": language, "set_slug": set_slug},
        ).all()
        for cid, vol in rows:
            if cid and vol is not None:
                vol_by_card[str(cid)] = float(vol)
    except Exception:
        # If volatility query fails for any reason, just omit vol (do not break targets).
        vol_by_card = {}

    targets: List[GradingTarget] = []
    for card_id, (raw_cnt, raw_med) in raw_by_card.items():
        if raw_cnt < min_raw_sales:
            continue
        g_total = graded_count_by_card.get(card_id, 0)
        if g_total < min_graded_sales:
            continue
        if sales_per_week.get(card_id, 0.0) < min_sales_per_week:
            continue
        if max_volatility is not None:
            v = vol_by_card.get(card_id)
            if v is not None and v > max_volatility:
                continue

        best_company = None
        best_ev = None
        best_up = None

        # EV per company = Σ P(g)*median(company,g)
        for company, grades in graded.get(card_id, {}).items():
            denom = sum(c for c, _m in grades.values())
            if denom <= 0:
                continue
            ev = 0.0
            for _gv, (cnt, med) in grades.items():
                ev += (cnt / denom) * med
            upside = ev - raw_med - grading_cost_usd
            if best_up is None or upside > best_up:
                best_up = upside
                best_company = company
                best_ev = ev

        if best_up is None:
            continue
        if min_upside_usd is not None and best_up < min_upside_usd:
            continue

        # Split card_id into set/card slug
        set_part = None
        card_part = None
        if "/" in card_id:
            set_part, card_part = card_id.split("/", 1)

        targets.append(
            GradingTarget(
                card_id=card_id,
                name=name_map.get(card_id, card_id),
                set_slug=set_part,
                card_slug=card_part,
                raw_count=raw_cnt,
                raw_median_usd=round(raw_med, 2),
                graded_count=g_total,
                best_company=best_company,
                best_ev_usd=round(best_ev, 2) if best_ev is not None else None,
                best_upside_usd=round(best_up, 2) if best_up is not None else None,
                sales_per_week=round(sales_per_week.get(card_id, 0.0), 3),
                volatility=round(vol_by_card.get(card_id), 6) if card_id in vol_by_card else None,
            )
        )

    # Rank by best_upside then liquidity
    targets.sort(
        key=lambda t: (
            t.best_upside_usd if t.best_upside_usd is not None else -1e9,
            t.sales_per_week,
        ),
        reverse=True,
    )
    targets = targets[:limit]

    return GradingTargetsResponse(
        grading_cost_usd=grading_cost_usd,
        language_filter=language,
        set_slug_filter=set_slug,
        min_raw_sales=min_raw_sales,
        min_graded_sales=min_graded_sales,
        limit=limit,
        targets=targets,
    )

