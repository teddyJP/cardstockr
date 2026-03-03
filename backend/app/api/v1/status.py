from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Sale


router = APIRouter()


@router.get("", tags=["status"])
def status(db: Session = Depends(get_db)) -> dict:
    """
    Lightweight ingest/status endpoint.

    Returns:
    - total_sales: count of all rows in sales
    - ebay_sales: count of rows with source='ebay_api'
    - last_sale_at: max sold_at over all sales
    - last_ebay_sale_at: max sold_at where source='ebay_api'
    """
    total_sales = db.execute(select(func.count(Sale.id))).scalars().first() or 0
    ebay_sales = (
        db.execute(select(func.count(Sale.id)).where(Sale.source == "ebay_api"))
        .scalars()
        .first()
        or 0
    )

    last_sale_at = db.execute(select(func.max(Sale.sold_at))).scalars().first()
    last_ebay_sale_at = (
        db.execute(select(func.max(Sale.sold_at)).where(Sale.source == "ebay_api"))
        .scalars()
        .first()
    )

    def _iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if isinstance(dt, datetime) else None

    return {
        "total_sales": int(total_sales),
        "ebay_sales": int(ebay_sales),
        "last_sale_at": _iso(last_sale_at),
        "last_ebay_sale_at": _iso(last_ebay_sale_at),
    }

