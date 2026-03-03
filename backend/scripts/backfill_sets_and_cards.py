"""
Backfill sets and card_identities from sales titles, and set sales.card_id to canonical set_slug/card_slug.

Run from backend/: python -m scripts.backfill_sets_and_cards

This allows browse-by-set and stable URLs like /game/pokemon-ascended-heroes/mega-gengar-ex-284.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, engine
from app.db.models import Base, Sale, Set, CardIdentity
from app.services.title_parser import (
    parse_card_name,
    parse_card_number,
    parse_condition,
    parse_set_and_card_slugs,
    parse_set_from_title,
    parse_variant,
)


def _ensure_schema() -> None:
    """
    Minimal schema migration for MVP.

    This project has evolved without Alembic migrations, so existing DBs may be missing columns.
    We add what we need in an idempotent way.
    """
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE card_identities ADD COLUMN IF NOT EXISTS set_id INTEGER REFERENCES sets(id)"
        ))
        conn.execute(text(
            "ALTER TABLE card_identities ADD COLUMN IF NOT EXISTS card_slug VARCHAR(255)"
        ))
        conn.execute(text(
            "ALTER TABLE card_identities ADD COLUMN IF NOT EXISTS image_url VARCHAR(512)"
        ))
        conn.execute(text(
            "ALTER TABLE card_identities ADD COLUMN IF NOT EXISTS variant VARCHAR(255)"
        ))
        # Ensure USD-normalized price column exists (used by metrics and charts)
        conn.execute(text(
            "ALTER TABLE sales ADD COLUMN IF NOT EXISTS total_price_usd DOUBLE PRECISION"
        ))
        # Ensure grade_value is float-capable (for 9.5 etc.)
        try:
            conn.execute(text(
                "ALTER TABLE sales ALTER COLUMN grade_value TYPE DOUBLE PRECISION USING grade_value::double precision"
            ))
        except Exception:
            # If it already is DOUBLE PRECISION (or cannot be cast), skip.
            pass
        conn.commit()


def main() -> None:
    _ensure_schema()
    db = SessionLocal()
    try:
        # Distinct titles from sales
        rows = db.execute(select(Sale.title).distinct()).scalars().all()
        titles = [r[0] for r in rows if r[0]]
        print(f"Found {len(titles)} distinct titles in sales")

        sets_by_slug: dict = {}
        cards_by_id: dict = {}

        for title in titles:
            set_slug, card_slug = parse_set_and_card_slugs(title)
            set_name = parse_set_from_title(title)
            card_name = parse_card_name(title)
            card_number = parse_card_number(title)
            condition = parse_condition(title)
            variant = parse_variant(title)

            card_id = f"{set_slug}/{card_slug}"

            if set_slug not in sets_by_slug:
                existing = db.execute(select(Set).where(Set.set_slug == set_slug)).scalars().first()
                if existing:
                    sets_by_slug[set_slug] = existing
                else:
                    s = Set(set_slug=set_slug, set_name=set_name, game="Pokemon")
                    db.add(s)
                    db.flush()
                    sets_by_slug[set_slug] = s

            set_row = sets_by_slug[set_slug]
            if card_id not in cards_by_id:
                existing = db.execute(select(CardIdentity).where(CardIdentity.card_id == card_id)).scalars().first()
                if existing:
                    # Update existing identity with cleaned canonical fields
                    existing.set_id = set_row.id
                    existing.card_slug = card_slug
                    existing.name = card_name[:255] or existing.name
                    existing.set_name = set_name or existing.set_name
                    existing.number = card_number or existing.number
                    existing.variant = variant or existing.variant
                    cards_by_id[card_id] = existing
                else:
                    c = CardIdentity(
                        set_id=set_row.id,
                        card_slug=card_slug,
                        card_id=card_id,
                        name=card_name[:255],
                        set_name=set_name,
                        number=card_number,
                        variant=variant,
                    )
                    db.add(c)
                    db.flush()
                    cards_by_id[card_id] = c

            # Update all sales with this title to use this card_id
            db.execute(
                update(Sale)
                .where(Sale.title == title)
                .values(
                    card_id=card_id,
                    set_name=set_name,
                    card_number=card_number,
                    player_or_pokemon_name=card_name[:255],
                    condition_raw=condition,
                )
            )

        db.commit()
        print(f"Created/updated {len(sets_by_slug)} sets, {len(cards_by_id)} cards. Updated sales.card_id.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
