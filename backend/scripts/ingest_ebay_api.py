"""
Ingest completed Pokémon sales from eBay Finding API into the sales table.

Requires EBAY_APP_ID in environment or .env. Uses sandbox by default; set
EBAY_SANDBOX=false for production.

- Converts all amounts to USD (total_price_usd).
- Sets language from title: en | jp | other.
- Sets grade_company / grade_value from title (None = raw).

Bucketing (for later metrics):
- All 10s:     WHERE grade_value >= 9.99
- All PSA:     WHERE grade_company = 'PSA'
- PSA 10:      WHERE grade_company = 'PSA' AND grade_value >= 9.99
"""

import os
import sys

# So that app package is importable when running as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.db.database import SessionLocal, engine
from app.db.models import Base
from app.services.ebay_ingest import EBAY_CATEGORY_POKEMON_SINGLES, run_ingest


def main() -> None:
    settings = get_settings()
    app_id = getattr(settings, "ebay_app_id", None) or ""
    if not app_id:
        print("Set EBAY_APP_ID in .env or environment and try again.")
        sys.exit(1)

    print(f"Using eBay {'sandbox' if getattr(settings, 'ebay_sandbox', True) else 'production'}")
    print(f"Category: {EBAY_CATEGORY_POKEMON_SINGLES} (Pokémon Singles)")
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        total = run_ingest(
            session,
            category_id=EBAY_CATEGORY_POKEMON_SINGLES,
            keywords=None,  # optional: "Charizard" to narrow
            max_pages=5,
        )
        print(f"Ingested {total} new sale(s).")
    finally:
        session.close()


if __name__ == "__main__":
    main()
