from typing import List, Optional

from pydantic import BaseModel


class GradingTarget(BaseModel):
    card_id: str  # canonical set_slug/card_slug
    name: str
    set_slug: Optional[str] = None
    card_slug: Optional[str] = None

    raw_count: int
    raw_median_usd: float

    graded_count: int
    best_company: Optional[str] = None
    best_ev_usd: Optional[float] = None
    best_upside_usd: Optional[float] = None

    sales_per_week: float
    volatility: Optional[float] = None  # std dev of simple returns, proxy for risk


class GradingTargetsResponse(BaseModel):
    grading_cost_usd: float
    language_filter: Optional[str] = None
    set_slug_filter: Optional[str] = None
    min_raw_sales: int
    min_graded_sales: int
    limit: int
    targets: List[GradingTarget]

