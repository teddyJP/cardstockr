from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class PriceByGrade(BaseModel):
    """One row in the PriceCharting-style price table."""
    label: str  # "Ungraded", "PSA 10", "BGS 9.5", ...
    grade_company: Optional[str] = None
    grade_value: Optional[float] = None
    median_price_usd: float
    count: int


class GradeCount(BaseModel):
    """Count of sales at a given grade (for distribution/population)."""
    grade_value: float
    count: int


class CompanyGradeDistribution(BaseModel):
    """Grade distribution for one company (sales count per grade)."""
    company: str
    total_graded: int
    by_grade: List[GradeCount]
    ten_rate: Optional[float] = None  # fraction that are grade 10


class GradingUpside(BaseModel):
    """Is grading worth it? EV vs raw, per company."""
    raw_median_usd: float
    grading_cost_usd: float
    by_company: List[dict]  # [{ "company": "PSA", "ev_usd": 1200, "upside_usd": 150, "worth_grading": True }, ...]
    worth_grading_any: bool  # True if any company has upside > 0


class RawConditionBucket(BaseModel):
    """Aggregated raw (ungraded) prices by condition bucket (NM, LP, etc)."""

    median_price_usd: float
    count: int


class CompanyPriceBand(BaseModel):
    """Low/median/high band for graded prices per company."""

    company: str
    low_usd: Optional[float] = None
    median_usd: Optional[float] = None
    high_usd: Optional[float] = None
    sales_count: int = 0


class CardSearchResult(BaseModel):
    card_id: str
    name: str
    set_name: str
    year: int
    number: str
    variant: Optional[str] = None
    set_slug: Optional[str] = None
    image_url: Optional[str] = None
    grade_company: Optional[str] = None
    grade_value: Optional[float] = None
    # Optional PriceCharting-style summary for search rows
    raw_median_usd: Optional[float] = None
    raw_low_usd: Optional[float] = None
    raw_high_usd: Optional[float] = None
    raw_sales_count: int = 0


class CardTimeSeriesPoint(BaseModel):
    date: date
    median_price: float
    sales_count: int


class CardForecastPoint(BaseModel):
    date: date
    p10: float
    p50: float
    p90: float


class CardDetail(BaseModel):
    card_id: str
    name: str
    set_name: str
    year: int
    number: str
    variant: Optional[str] = None
    grade_company: Optional[str] = None
    grade_value: Optional[float] = None
    canonical_card_id: Optional[str] = None  # set_slug/card_slug when available
    set_slug: Optional[str] = None
    card_slug: Optional[str] = None
    image_url: Optional[str] = None

    fair_value_now: float
    fair_value_ci_low: float
    fair_value_ci_high: float

    forecast_horizon_days: int
    liquidity_score: int
    risk_score: int

    # Trend: % change in median price (recent window vs previous window)
    change_30d_pct: Optional[float] = None
    change_90d_pct: Optional[float] = None

    # Raw value band across all ungraded sales
    raw_low_usd: Optional[float] = None
    raw_median_usd: Optional[float] = None
    raw_high_usd: Optional[float] = None
    raw_sales_count: int = 0

    # Recent-window aggregates (PriceCharting-style "current value")
    recent_window_days: int = 90
    recent_raw_by_condition: Dict[str, RawConditionBucket] = {}
    recent_prices_by_grade: List[PriceByGrade] = []

    history: List[CardTimeSeriesPoint]
    forecast: List[CardForecastPoint]

    # PriceCharting-style: prices by grade (all companies), distribution, grading upside
    prices_by_grade: List[PriceByGrade] = []
    grade_distribution: List[CompanyGradeDistribution] = []
    grading_upside: Optional[GradingUpside] = None

    # Graded value band per company
    graded_price_bands: List[CompanyPriceBand] = []

    # Raw price by condition (Damaged/HP/MP/LP/NM)
    raw_by_condition: Dict[str, RawConditionBucket] = {}

    recent_sales: List[dict] = []

    last_updated: Optional[datetime] = None


class CardSeriesPoint(BaseModel):
    date: date
    median_price_usd: float
    sales_count: int


class CardSeriesLine(BaseModel):
    label: str  # "Raw", "PSA", "BGS", ...
    grade_company: Optional[str] = None
    points: List[CardSeriesPoint]


class CardSeriesResponse(BaseModel):
    canonical_card_id: Optional[str] = None
    group_by: str  # "combined" | "company"
    companies: List[str] = []
    grades: List[float] = []
    include_raw: bool = True
    series: List[CardSeriesLine]

