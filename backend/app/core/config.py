from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    app_name: str = "TCG Predictor API"
    environment: str = Field("local", description="Environment name (local/dev/prod)")

    # Database
    database_url: str = Field(
        # Local default (running python directly on your machine).
        # When running in Docker, `docker-compose.yml` sets DATABASE_URL to use host `db`.
        "postgresql+psycopg2://tcg_user:tcg_pass@localhost:5432/tcg_db",
        description="SQLAlchemy database URL",
    )

    # eBay Finding API (completed/sold items)
    ebay_app_id: str = Field("", description="eBay App ID (Client ID) for Finding API")
    ebay_dev_id: str = Field("", description="eBay Dev ID (optional, for some APIs)")
    ebay_sandbox: bool = Field(True, description="Use eBay sandbox (True) or production")
    ebay_global_id: str = Field("EBAY_US", description="eBay marketplace, e.g. EBAY_US")
    ebay_default_currency: str = Field("USD", description="Default currency for reporting")

    # eBay Marketplace Account Deletion (required for production keyset; full HTTPS URL you register in the portal)
    ebay_account_deletion_token: str = Field("", description="Verification token for account-deletion webhook (32–80 chars)")
    ebay_account_deletion_endpoint_url: str = Field("", description="Full HTTPS URL of this webhook, e.g. https://your-api.com/api/webhooks/ebay/account-deletion")

    # Currency conversion to USD (optional API key for live rates; else fallback rates used)
    exchange_rate_api_key: str = Field("", description="Optional: API key for exchange rate API")
    exchange_rate_api_url: str = Field(
        "https://api.exchangerate-api.com/v4/latest/USD",
        description="Optional: URL for exchange rate JSON (no key needed for exchangerate-api.com)",
    )

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """SQLAlchemy needs postgresql+psycopg2://; some hosts give postgres:// or postgresql://."""
        if not v:
            return v
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg2://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+"):
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()

