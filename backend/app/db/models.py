from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Set(Base):
    """Canonical set (e.g. Pokemon Ascended Heroes). Used for browse-by-set and stable URLs."""
    __tablename__ = "sets"

    id = Column(Integer, primary_key=True, index=True)
    set_slug = Column(String(255), unique=True, index=True, nullable=False)  # e.g. pokemon-ascended-heroes
    set_name = Column(String(255), nullable=False)
    game = Column(String(64), nullable=True)  # e.g. Pokemon


class CardIdentity(Base):
    __tablename__ = "card_identities"

    id = Column(Integer, primary_key=True, index=True)
    set_id = Column(Integer, ForeignKey("sets.id"), nullable=True, index=True)
    card_slug = Column(String(255), nullable=True, index=True)  # e.g. mega-gengar-ex-284
    # Global id for lookups: set_slug/card_slug when set_id is set, else legacy (e.g. full title)
    card_id = Column(String(512), unique=True, index=True, nullable=False)

    name = Column(String(255), nullable=False)
    set_name = Column(String(255), nullable=True)
    year = Column(Integer, nullable=True)
    number = Column(String(64), nullable=True)
    variant = Column(String(255), nullable=True)
    language = Column(String(64), nullable=True)
    image_url = Column(String(512), nullable=True)  # Pokémon TCG API or other CDN

    alias_patterns = Column(Text, nullable=True)  # For title parsing heuristics

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (Index("ix_card_identities_set_slug", "set_id", "card_slug"),)


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)

    source = Column(String(64), nullable=False)  # ebay, tcgplayer, etc.
    sold_at = Column(DateTime, nullable=False, index=True)

    title = Column(Text, nullable=False)

    price = Column(Float, nullable=False)
    shipping = Column(Float, nullable=True)
    total_price = Column(Float, nullable=False)
    total_price_usd = Column(Float, nullable=True)  # Normalized to USD for cross-currency metrics
    currency = Column(String(8), nullable=False, default="USD")

    condition_raw = Column(Text, nullable=True)
    grade_company = Column(String(32), nullable=True)
    grade_value = Column(Float, nullable=True)  # 10, 9.5, 9, etc.

    set_name = Column(String(255), nullable=True)
    year = Column(Integer, nullable=True)
    card_number = Column(String(64), nullable=True)
    player_or_pokemon_name = Column(String(255), nullable=True)
    variant = Column(String(255), nullable=True)
    language = Column(String(64), nullable=True)

    seller_feedback = Column(Integer, nullable=True)
    listing_id = Column(String(255), nullable=False)

    card_id = Column(String(255), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "listing_id", name="uq_sales_source_listing"),
        Index(
            "ix_sales_card_grade_date",
            "card_id",
            "grade_company",
            "grade_value",
            "sold_at",
        ),
        Index("ix_sales_language", "language"),
        Index("ix_sales_grade_bucket", "grade_company", "grade_value"),
    )

