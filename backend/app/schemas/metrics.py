from typing import Dict, List, Optional

from pydantic import BaseModel


class GradeBucket(BaseModel):
    """Aggregates for one grade (e.g. 10, 9.5, or 'raw')."""
    grade_label: str  # "10", "9.5", "raw"
    count: int
    median_price_usd: Optional[float] = None


class CompanyGradeBucket(BaseModel):
    """Aggregates for one company+grade (e.g. PSA 10)."""
    grade_value: Optional[float] = None  # 10, 9.5, 9, ...
    count: int
    median_price_usd: Optional[float] = None


class CompanyBucket(BaseModel):
    """Aggregates for one grading company (e.g. PSA), with per-grade breakdown."""
    company: str
    count: int
    median_price_usd: Optional[float] = None
    grade_breakdown: List[CompanyGradeBucket] = []


class ByGradeResponse(BaseModel):
    buckets: List[GradeBucket]
    language_filter: Optional[str] = None


class ByCompanyResponse(BaseModel):
    buckets: List[CompanyBucket]
    language_filter: Optional[str] = None


class TenRateResponse(BaseModel):
    """Fraction of graded sales that are grade 10 (overall and per company)."""
    overall_ten_rate: Optional[float] = None  # null if no graded sales
    graded_count: int
    ten_count: int
    by_company: Dict[str, float] = {}  # company -> ten_rate


class MetricsSummaryResponse(BaseModel):
    total_sales: int
    by_language: Dict[str, int] = {}
    raw_count: int
    graded_count: int


class MoverCard(BaseModel):
    """Top movers (PriceCharting-style) for a given window."""

    card_id: str
    name: str
    set_slug: Optional[str] = None
    set_name: Optional[str] = None
    window_days: int
    value_now_usd: Optional[float] = None
    value_prev_usd: Optional[float] = None
    change_pct: Optional[float] = None
    sales_now: int = 0
    sales_prev: int = 0


class MoversResponseBase(BaseModel):
    window_days: int
    min_sales_now: int
    min_sales_prev: int
    cards: List[MoverCard]
