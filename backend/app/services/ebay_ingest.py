"""
Ingest completed (sold) Pokémon listings from eBay Finding API.

Stores each sale with:
- total_price_usd (converted from original currency)
- language: en | jp | other (from title)
- grade_company / grade_value (from title; None = raw)

Bucketing for metrics:
- By grade: WHERE grade_value = 10 (all 10s)
- By company: WHERE grade_company = 'PSA'
- By company+grade: WHERE grade_company = 'PSA' AND grade_value = 10
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Sale
from app.services.currency import to_usd
from app.services.title_parser import parse_grade, parse_language

# Pokémon Singles category on eBay US
EBAY_CATEGORY_POKEMON_SINGLES = "183454"

# Finding API base URLs
EBAY_FINDING_SANDBOX = "https://svcs.sandbox.ebay.com/services/search/FindingService/v1"
EBAY_FINDING_PROD = "https://svcs.ebay.com/services/search/FindingService/v1"


def _get_base_url(sandbox: bool) -> str:
    return EBAY_FINDING_SANDBOX if sandbox else EBAY_FINDING_PROD


def _parse_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract from one API item: listing_id, title, price, currency, sold_at."""
    # Handle both {"itemId": "123"} and {"itemId": ["123"]}
    item_id = item.get("itemId")
    if isinstance(item_id, list):
        item_id = item_id[0] if item_id else None
    if not item_id:
        return None

    title = item.get("title")
    if isinstance(title, list):
        title = title[0] if title else ""
    title = title or ""

    # sellingStatus.currentPrice
    selling = item.get("sellingStatus") or {}
    if isinstance(selling, list):
        selling = selling[0] if selling else {}
    current = selling.get("currentPrice") or {}
    if isinstance(current, list):
        current = current[0] if current else {}
    price_val = current.get("value") or current.get("__value__")
    currency = current.get("currencyId") or current.get("_currencyId") or "USD"
    if price_val is None:
        return None
    try:
        price = float(price_val)
    except (TypeError, ValueError):
        return None

    # listingInfo.endTime (sold_at)
    listing_info = item.get("listingInfo") or {}
    if isinstance(listing_info, list):
        listing_info = listing_info[0] if listing_info else {}
    end_time = listing_info.get("endTime") or listing_info.get("_endTime")
    sold_at = None
    if end_time:
        try:
            # ISO format or eBay format
            sold_at = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except Exception:
            try:
                sold_at = datetime.strptime(end_time[:19], "%Y-%m-%dT%H:%M:%S")
            except Exception:
                pass
    if sold_at is None:
        sold_at = datetime.utcnow()

    return {
        "listing_id": str(item_id),
        "title": title,
        "price": price,
        "shipping": 0.0,  # Finding API often doesn't include shipping in currentPrice
        "currency": currency,
        "sold_at": sold_at,
    }


def fetch_completed_items(
    category_id: str = EBAY_CATEGORY_POKEMON_SINGLES,
    keywords: Optional[str] = None,
    page: int = 1,
    per_page: int = 100,
) -> List[Dict[str, Any]]:
    """
    Call eBay Finding API findCompletedItems. Returns list of parsed item dicts.
    """
    settings = get_settings()
    app_id = getattr(settings, "ebay_app_id", None) or ""
    if not app_id:
        raise ValueError("ebay_app_id is not set in config or .env")

    base = _get_base_url(getattr(settings, "ebay_sandbox", True))
    global_id = getattr(settings, "ebay_global_id", "EBAY_US")

    params = {
        "OPERATION-NAME": "findCompletedItems",
        "SERVICE-VERSION": "1.0.0",
        "SECURITY-APPNAME": app_id,
        "GLOBAL-ID": global_id,
        "RESPONSE-DATA-FORMAT": "JSON",
        "REST-PAYLOAD": "true",
        "categoryId": category_id,
        "paginationInput.entriesPerPage": per_page,
        "paginationInput.pageNumber": page,
    }
    if keywords:
        params["keywords"] = keywords

    url = f"{base}?{urlencode(params)}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Navigate response: findCompletedItemsResponse -> searchResult -> item
    response = data.get("findCompletedItemsResponse") or []
    if isinstance(response, list):
        response = response[0] if response else {}
    search_result = response.get("searchResult") or response.get("searchResult", [])
    if isinstance(search_result, list):
        search_result = search_result[0] if search_result else {}
    items = search_result.get("item") or []
    if not isinstance(items, list):
        items = [items]

    out = []
    for it in items:
        parsed = _parse_item(it)
        if parsed:
            out.append(parsed)
    return out


def ingest_page_into_db(
    session: Session,
    items: List[Dict[str, Any]],
    source: str = "ebay_api",
) -> int:
    """
    Insert items into sales table. Converts to USD, sets language and grade from title.
    Returns count of newly inserted rows (skips duplicates by source+listing_id).
    """
    inserted = 0
    for row in items:
        listing_id = row["listing_id"]
        title = row["title"]
        price = row["price"]
        shipping = row.get("shipping") or 0
        total = price + shipping
        currency = (row.get("currency") or "USD").upper()
        total_usd = to_usd(total, currency)

        language = parse_language(title)
        grade_company, grade_value = parse_grade(title)

        existing = session.execute(
            select(Sale).where(
                Sale.source == source,
                Sale.listing_id == listing_id,
            )
        ).scalars().first()
        if existing:
            continue

        sale = Sale(
            source=source,
            sold_at=row["sold_at"],
            title=title,
            price=price,
            shipping=shipping,
            total_price=total,
            total_price_usd=total_usd,
            currency=currency,
            condition_raw=None,
            grade_company=grade_company,
            grade_value=grade_value,
            set_name=None,
            year=None,
            card_number=None,
            player_or_pokemon_name=None,
            variant=None,
            language=language,
            seller_feedback=None,
            listing_id=listing_id,
            card_id=None,
        )
        session.add(sale)
        inserted += 1
    session.commit()
    return inserted


def run_ingest(
    session: Session,
    category_id: str = EBAY_CATEGORY_POKEMON_SINGLES,
    keywords: Optional[str] = None,
    max_pages: int = 5,
) -> int:
    """
    Fetch up to max_pages of completed items and ingest into sales.
    Returns total number of new rows inserted.
    """
    total_inserted = 0
    for page in range(1, max_pages + 1):
        items = fetch_completed_items(
            category_id=category_id,
            keywords=keywords,
            page=page,
            per_page=100,
        )
        if not items:
            break
        n = ingest_page_into_db(session, items, source="ebay_api")
        total_inserted += n
        if n == 0 and page == 1:
            break
    return total_inserted
