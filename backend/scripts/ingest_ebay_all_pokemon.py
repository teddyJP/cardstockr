"""
Batch ingest of completed Pokémon TCG singles from eBay into the `sales` table.

Usage (from backend/):

    source venv/bin/activate
    python -m scripts.ingest_ebay_all_pokemon --max-pages 10

You can run this on a schedule (e.g. cron) to approximate continuous ingestion.
Because `sales` enforces (source, listing_id) uniqueness via the ingest logic,
rerunning with overlapping windows is safe.
"""

import argparse

from app.db.database import SessionLocal
from app.services.ebay_ingest import EBAY_CATEGORY_POKEMON_SINGLES, run_ingest


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest completed Pokémon singles from eBay into sales table.")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Maximum pages to fetch from eBay (100 items per page).",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default=None,
        help="Optional keyword filter (e.g. 'Charizard'). Leave unset for all Pokémon singles.",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        inserted = run_ingest(
            session=session,
            category_id=EBAY_CATEGORY_POKEMON_SINGLES,
            keywords=args.keywords,
            max_pages=args.max_pages,
        )
        print(f"Ingested {inserted} new sales rows from eBay (Pokémon singles).")
    finally:
        session.close()


if __name__ == "__main__":
    main()

