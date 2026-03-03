"""
Backfill card_identities.image_url from Pokémon TCG API.

Run from backend/: python -m scripts.backfill_card_images

Skips rows that already have image_url. Uses set_name + number to look up the card.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import CardIdentity
from app.services.card_image import resolve_card_image


def main() -> None:
    db = SessionLocal()
    try:
        stmt = select(CardIdentity).where(
            CardIdentity.set_name.isnot(None),
            CardIdentity.number.isnot(None),
            CardIdentity.number != "",
            CardIdentity.number != "-",
        )
        identities = db.execute(stmt).scalars().all()
        print(f"Found {len(identities)} card identities with set_name and number")

        updated = 0
        for ident in identities:
            if getattr(ident, "image_url", None):
                continue
            url = resolve_card_image(ident.set_name, ident.number)
            if url:
                ident.image_url = url[:512]
                updated += 1
                if updated % 10 == 0:
                    db.commit()
                    print(f"  Updated {updated} images…")
            time.sleep(0.2)  # be nice to the API

        db.commit()
        print(f"Done. Set image_url for {updated} cards.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
