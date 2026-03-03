"""
Stub script for ingesting eBay sold CSV exports into the `sales` table.

In v1, you will:
1. Export sold listings from eBay as CSV.
2. Place the CSV into `data/samples/`.
3. Run this script to parse and insert rows into the database.
"""

from pathlib import Path
import argparse
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import engine
from app.db.models import Base, Sale
from app.services.currency import to_usd
from app.services.title_parser import parse_grade, parse_language


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def _read_ebay_order_earnings(csv_path: Path) -> pd.DataFrame:
    """
    Read an eBay "Order earnings" CSV, skipping the explanatory header section.

    This file typically has a bunch of descriptive lines before the real header row
    that starts with "Order creation date,...".
    """
    header_row_index = None
    with csv_path.open("r", encoding="utf-8-sig") as f:
        for i, line in enumerate(f):
            if line.startswith("Order creation date"):
                header_row_index = i
                break

    if header_row_index is None:
        # Fall back to a normal read; user might have a different CSV format.
        return pd.read_csv(csv_path)

    # Skip everything before the header row so pandas treats it as the header.
    df = pd.read_csv(csv_path, skiprows=header_row_index)
    return df


def ingest_csv(csv_path: Path, source: str = "ebay") -> None:
    # For now we assume eBay "Order earnings" report format.
    df = _read_ebay_order_earnings(csv_path)

    # Normalize column names to something easier to work with
    df.columns = [str(c).strip() for c in df.columns]

    with Session(bind=engine, future=True) as session:
        for _, row in df.iterrows():
            # Parse order creation date into a proper datetime
            sold_at_raw = row.get("Order creation date")
            sold_at: datetime | None = None
            if isinstance(sold_at_raw, str) and sold_at_raw.strip():
                # Examples: "Dec 2, 2025"
                try:
                    sold_at = datetime.strptime(sold_at_raw.split(",")[0] + "," + sold_at_raw.split(",")[1], "%b %d, %Y")
                except Exception:
                    # Fallback: let pandas try
                    sold_at = pd.to_datetime(sold_at_raw, errors="coerce")

            title = row.get("Item title") or ""
            price = float(row.get("Item price", 0) or 0)
            shipping = float(row.get("Shipping and handling", 0) or 0)
            total_price = float(row.get("Gross amount", 0) or 0)
            currency = (row.get("Transaction currency") or "USD").strip()
            total_price_usd = to_usd(total_price, currency)
            language = parse_language(title)
            grade_company, grade_value = parse_grade(title)

            sale = Sale(
                source=source,
                sold_at=sold_at or datetime.utcnow(),
                title=title,
                price=price,
                shipping=shipping,
                total_price=total_price,
                total_price_usd=total_price_usd,
                currency=currency,
                condition_raw=row.get("condition", None),
                grade_company=grade_company,
                grade_value=grade_value,
                set_name=None,
                year=None,
                card_number=None,
                player_or_pokemon_name=None,
                variant=None,
                language=language,
                seller_feedback=None,
                listing_id=str(row.get("Item ID")),
                card_id=None,
            )
            session.add(sale)

        session.commit()


def main() -> None:
    settings = get_settings()
    print(f"Ingest running against DB: {settings.database_url}")

    init_db()

    parser = argparse.ArgumentParser(description="Ingest sold listings CSV(s) into the DB.")
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=None,
        help="Optional path to a single CSV file to ingest.",
    )
    parser.add_argument(
        "--source",
        dest="source",
        default="ebay",
        help="Source name to store in the sales table (default: ebay).",
    )
    args = parser.parse_args()

    if args.csv_path:
        csv_file = Path(args.csv_path).expanduser().resolve()
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        print(f"Ingesting {csv_file}...")
        ingest_csv(csv_file, source=args.source)
        print("Ingestion complete.")
        return

    # Default: ingest all CSVs from repo-level `data/samples/`
    # (repo_root = .../tcg-tool, script lives at .../tcg-tool/backend/scripts/ingest_sales.py)
    repo_root = Path(__file__).resolve().parents[2]
    samples_dir = repo_root / "data" / "samples"

    csv_files = sorted(samples_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {samples_dir}. Place eBay exports there.")
        return

    for csv_file in csv_files:
        print(f"Ingesting {csv_file}...")
        ingest_csv(csv_file, source=args.source)

    print("Ingestion complete.")


if __name__ == "__main__":
    main()

