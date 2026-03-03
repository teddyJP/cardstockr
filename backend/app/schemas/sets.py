from typing import List, Optional

from pydantic import BaseModel


class SetSummary(BaseModel):
    set_slug: str
    set_name: str
    game: Optional[str] = None
    card_count: int = 0


class CardInSet(BaseModel):
    card_id: str
    card_slug: str
    name: str
    set_name: Optional[str] = None
    number: Optional[str] = None
    image_url: Optional[str] = None
    variant: Optional[str] = None


class SetTopCard(BaseModel):
    card_id: str
    name: str
    value_usd: float
    change_pct: Optional[float] = None
    sales_per_week: Optional[float] = None


class SetAnalytics(BaseModel):
    set_slug: str
    set_name: str
    total_sales: int
    raw_sales: int
    graded_sales: int

    language_filter: Optional[str] = None

    top_movers_30d: List[SetTopCard] = []
    top_movers_90d: List[SetTopCard] = []
    top_liquidity: List[SetTopCard] = []

    # Set index: daily median price across the set (in USD)
    index_history: List[dict] = []
