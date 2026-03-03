"""
Resolve Pokémon card image URL from Pokémon TCG API.
Used by card detail API and by backfill_card_images script.
"""

from typing import Optional

import requests

POKEMON_TCG_API_BASE = "https://api.pokemontcg.io/v2"


def resolve_card_image(set_name: Optional[str], number: Optional[str]) -> Optional[str]:
    """
    Try to resolve card image URL from Pokémon TCG API by set name and number.
    Returns images.large URL or None on failure/missing.
    """
    if not set_name or not number or number == "-":
        return None
    number_clean = (number or "").strip()
    if "/" in number_clean:
        number_clean = number_clean.split("/")[0].strip()
    if not number_clean:
        return None
    try:
        q = f'set.name:"{set_name}" number:"{number_clean}"'
        r = requests.get(
            f"{POKEMON_TCG_API_BASE}/cards",
            params={"q": q, "pageSize": 1},
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        cards = data.get("data") or []
        if not cards:
            return None
        images = (cards[0] or {}).get("images") or {}
        return images.get("large") or images.get("small")
    except Exception:
        return None
