"""
Browse sets and cards in a set. Stable URLs: /game/{set_slug}/{card_slug}.

Also provides set analytics (PriceCharting-style): top movers and liquidity.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import CardIdentity, Sale, Set
from app.schemas.sets import CardInSet, SetAnalytics, SetSummary, SetTopCard

router = APIRouter()

PRICE_USD = func.coalesce(Sale.total_price_usd, Sale.total_price)
MEDIAN_USD = func.percentile_cont(0.5).within_group(PRICE_USD)


@router.get("", response_model=List[SetSummary])
def list_sets(
    q: Optional[str] = Query(None, description="Search by set name"),
    db: Session = Depends(get_db),
):
    """List all sets, optionally filtered by name. Each set includes card count."""
    stmt = select(Set)
    if q:
        stmt = stmt.where(Set.set_name.ilike(f"%{q}%"))
    stmt = stmt.order_by(Set.set_name.asc())
    sets = db.execute(stmt).scalars().all()

    out = []
    for s in sets:
        count = db.execute(select(func.count(CardIdentity.id)).where(CardIdentity.set_id == s.id)).scalars().first() or 0
        out.append(
            SetSummary(set_slug=s.set_slug, set_name=s.set_name, game=s.game, card_count=count)
        )
    return out


@router.get("/{set_slug}/cards", response_model=List[CardInSet])
def list_cards_in_set(
    set_slug: str,
    db: Session = Depends(get_db),
):
    """List cards in a set. Use card_id (set_slug/card_slug) for detail URL."""
    set_row = db.execute(select(Set).where(Set.set_slug == set_slug)).scalars().first()
    if not set_row:
        raise HTTPException(status_code=404, detail="Set not found")

    stmt = (
        select(CardIdentity)
        .where(CardIdentity.set_id == set_row.id)
        .order_by(CardIdentity.name.asc())
    )
    cards = db.execute(stmt).scalars().all()
    return [
        CardInSet(
            card_id=c.card_id,
            card_slug=c.card_slug or "",
            name=c.name,
            set_name=c.set_name,
            number=c.number,
            image_url=c.image_url,
            variant=c.variant,
        )
        for c in cards
    ]


@router.get("/{set_slug}/analytics", response_model=SetAnalytics)
def set_analytics(
    set_slug: str,
    language: Optional[str] = Query(None, description="Optional language filter: en, jp, other"),
    db: Session = Depends(get_db),
):
    """
    Set analytics:
    - total/raw/graded sales counts
    - top movers (30d / 90d) by median-price change between two windows
    - top liquidity by sales/week
    """
    set_row = db.execute(select(Set).where(Set.set_slug == set_slug)).scalars().first()
    if not set_row:
        raise HTTPException(status_code=404, detail="Set not found")

    base = [Sale.card_id.ilike(f"{set_slug}/%")]
    if language:
        base.append(Sale.language == language)

    total_sales = db.execute(select(func.count(Sale.id)).where(*base)).scalars().first() or 0
    raw_sales = (
        db.execute(select(func.count(Sale.id)).where(*base).where(Sale.grade_company.is_(None))).scalars().first()
        or 0
    )
    graded_sales = (
        db.execute(select(func.count(Sale.id)).where(*base).where(Sale.grade_company.isnot(None))).scalars().first()
        or 0
    )

    # Name map
    cards = db.execute(select(CardIdentity.card_id, CardIdentity.name).where(CardIdentity.set_id == set_row.id)).all()
    name_map = {str(cid): str(nm) for cid, nm in cards}

    # Liquidity: sales per week per card_id
    liq_rows = db.execute(
        select(
            Sale.card_id,
            func.count(Sale.id).label("n"),
            func.min(Sale.sold_at).label("min_dt"),
            func.max(Sale.sold_at).label("max_dt"),
            MEDIAN_USD.label("median_now"),
        )
        .where(*base)
        .group_by(Sale.card_id)
    ).all()

    top_liq: List[SetTopCard] = []
    for cid, n, min_dt, max_dt, med in liq_rows:
        if not cid or not min_dt or not max_dt:
            continue
        days = max(1, (max_dt.date() - min_dt.date()).days)
        spw = (float(n) / float(days)) * 7.0
        top_liq.append(
            SetTopCard(
                card_id=str(cid),
                name=name_map.get(str(cid), str(cid)),
                value_usd=float(med or 0.0),
                sales_per_week=round(spw, 3),
            )
        )
    top_liq.sort(key=lambda x: (x.sales_per_week or 0.0), reverse=True)
    top_liq = top_liq[:10]

    # Movers: compute median in recent 14d vs 14d ending 30d ago (and 90d ago)
    # We approximate in SQL using sold_at windows per card: recent_end = max(sold_at)
    # then use relative intervals from that.
    movers_sql = """
    WITH bounds AS (
      SELECT card_id, MAX(sold_at) AS end_dt
      FROM sales
      WHERE card_id ILIKE (:set_slug || '/%')
        AND (:language IS NULL OR language = :language)
      GROUP BY card_id
    ),
    base AS (
      SELECT s.card_id,
             b.end_dt,
             s.sold_at,
             COALESCE(s.total_price_usd, s.total_price) AS price
      FROM sales s
      JOIN bounds b ON b.card_id = s.card_id
      WHERE s.card_id ILIKE (:set_slug || '/%')
        AND (:language IS NULL OR s.language = :language)
    ),
    w AS (
      SELECT
        card_id,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY price) FILTER (
          WHERE sold_at >= end_dt - INTERVAL '13 days' AND sold_at <= end_dt
        ) AS recent_med,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY price) FILTER (
          WHERE sold_at >= end_dt - INTERVAL '43 days' AND sold_at <= end_dt - INTERVAL '30 days'
        ) AS prior30_med,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY price) FILTER (
          WHERE sold_at >= end_dt - INTERVAL '103 days' AND sold_at <= end_dt - INTERVAL '90 days'
        ) AS prior90_med
      FROM base
      GROUP BY card_id
    )
    SELECT card_id, recent_med, prior30_med, prior90_med
    FROM w
    """
    rows = db.execute(text(movers_sql), {"set_slug": set_slug, "language": language}).all()

    movers30: List[SetTopCard] = []
    movers90: List[SetTopCard] = []
    for cid, recent_med, prior30_med, prior90_med in rows:
        if not cid or recent_med is None:
            continue
        cid_s = str(cid)
        if prior30_med is not None and prior30_med > 0:
            ch = (float(recent_med) - float(prior30_med)) / float(prior30_med)
            movers30.append(
                SetTopCard(
                    card_id=cid_s,
                    name=name_map.get(cid_s, cid_s),
                    value_usd=float(recent_med),
                    change_pct=round(ch, 4),
                )
            )
        if prior90_med is not None and prior90_med > 0:
            ch = (float(recent_med) - float(prior90_med)) / float(prior90_med)
            movers90.append(
                SetTopCard(
                    card_id=cid_s,
                    name=name_map.get(cid_s, cid_s),
                    value_usd=float(recent_med),
                    change_pct=round(ch, 4),
                )
            )

    movers30.sort(key=lambda x: (x.change_pct or -1e9), reverse=True)
    movers90.sort(key=lambda x: (x.change_pct or -1e9), reverse=True)
    # Set index: daily median across all card_ids in this set
    idx_rows = db.execute(
        select(
            func.date(Sale.sold_at).label("d"),
            MEDIAN_USD.label("median"),
            func.count(Sale.id).label("n"),
        )
        .where(*base)
        .group_by(func.date(Sale.sold_at))
        .order_by(func.date(Sale.sold_at))
    ).all()
    index_history = [
        {"date": d.isoformat(), "median_price": float(med or 0.0), "sales_count": int(n)}
        for d, med, n in idx_rows
    ]

    return SetAnalytics(
        set_slug=set_row.set_slug,
        set_name=set_row.set_name,
        total_sales=int(total_sales),
        raw_sales=int(raw_sales),
        graded_sales=int(graded_sales),
        language_filter=language,
        top_movers_30d=movers30[:10],
        top_movers_90d=movers90[:10],
        top_liquidity=top_liq,
        index_history=index_history,
    )
