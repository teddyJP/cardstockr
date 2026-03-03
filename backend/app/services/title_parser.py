"""
Parse listing title for language (en/jp/other), grading (company + value), and set/card for slugs.

Used for: bucketing by grade, by company, and by (company, grade); backfilling sets and card identities.
"""

import re
from typing import Optional, Tuple


def slugify(s: str, max_len: int = 80) -> str:
    """Lowercase, replace non-alphanumeric with hyphens, collapse hyphens, strip."""
    if not s:
        return ""
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().strip())
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:max_len] if max_len else s


# Known Pokemon set name substrings (title often contains one of these)
KNOWN_SET_SUBSTRINGS = [
    "Ascended Heroes",
    "Fusion Strike",
    "Scarlet & Violet",
    "Paldean Fates",
    "Obsidian Flames",
    "151",
    "Crown Zenith",
    "Silver Tempest",
    "Lost Origin",
    "Brilliant Stars",
    "Pokemon GO",
    "Astral Radiance",
    "Battle Styles",
    "Shining Fates",
    "Vivid Voltage",
    "Champions Path",
    "Darkness Ablaze",
    "Rebel Clash",
    "Sword & Shield",
    "Sun & Moon",
    "Team Up",
    "Unified Minds",
    "Unbroken Bonds",
    "Base Set",
    "Evolving Skies",
    "Evolving Skies",
    "Swsh",
    "Sv01",
    "Sv1",
    "Sv2",
    "Sv3",
    "Sv4",
    "Sv5",
]

_CARD_NUMBER_PATTERN = re.compile(r"\b(\d{1,4})\s*/\s*(\d{1,4})\b")

# Very lightweight condition parsing for now (we'll split NM vs LP later)
_CONDITION_PATTERN = re.compile(r"\b(NM|NEAR\s*MINT|LP|LIGHTLY\s*PLAYED|MP|MODERATELY\s*PLAYED|HP|HEAVILY\s*PLAYED|DMG|DAMAGED)\b", re.IGNORECASE)

_NOISE_TOKENS = re.compile(
    r"\b(Pokemon|Pokémon|Card|TCG|Trading\s*Card\s*Game|Foil|Ultra\s*Rare|Secret\s*Rare|Illustration\s*Rare|IR|SIR|UR|NM|LP|MP|HP|DMG|Mint|Pack\s*Fresh|Sleeved|On\s*Open|Near\s*Mint|Lightly\s*Played|Moderately\s*Played|Heavily\s*Played|Damaged)\b",
    re.IGNORECASE,
)

_VARIANT_PATTERNS = [
    (re.compile(r"\bReverse\s+Holo\b", re.IGNORECASE), "Reverse Holo"),
    (re.compile(r"\bHolofoil\b", re.IGNORECASE), "Holo"),
    (re.compile(r"\bHolo\b", re.IGNORECASE), "Holo"),
    (re.compile(r"\bNon[-\s]?Holo\b", re.IGNORECASE), "Non-Holo"),
    (re.compile(r"\bFull\s+Art\b", re.IGNORECASE), "Full Art"),
    (re.compile(r"\bAlt(?:ernate)?\s+Art\b", re.IGNORECASE), "Alternate Art"),
    (re.compile(r"\bPok[eé]\s*Ball\b.*\bPattern\b", re.IGNORECASE), "Poké Ball pattern"),
]


def parse_card_number(title: str) -> Optional[str]:
    """Extract '156/264' from listing titles."""
    if not title or not isinstance(title, str):
        return None
    m = _CARD_NUMBER_PATTERN.search(title)
    if not m:
        return None
    return f"{m.group(1)}/{m.group(2)}"


def parse_variant(title: str) -> Optional[str]:
    """Extract a simple variant label (Reverse Holo, Holo, Full Art, etc)."""
    if not title or not isinstance(title, str):
        return None
    for pattern, label in _VARIANT_PATTERNS:
        if pattern.search(title):
            return label
    return None


def parse_condition(title: str) -> Optional[str]:
    """Extract a coarse condition tag like NM/LP/MP/HP/DMG."""
    if not title or not isinstance(title, str):
        return None
    m = _CONDITION_PATTERN.search(title)
    if not m:
        return None
    v = m.group(1).upper().replace(" ", "")
    # Normalize long forms
    if v.startswith("NEARMINT"):
        return "NM"
    if v.startswith("LIGHTLYPLAYED"):
        return "LP"
    if v.startswith("MODERATELYPLAYED"):
        return "MP"
    if v.startswith("HEAVILYPLAYED"):
        return "HP"
    if v.startswith("DAMAGED"):
        return "DMG"
    return v


def parse_card_name(title: str) -> str:
    """
    Extract a canonical-ish card name string (e.g. 'Gengar V') from noisy listing titles.
    Heuristic:
    - take text before card number if present
    - remove common noise tokens
    - collapse whitespace
    """
    if not title or not isinstance(title, str):
        return "Unknown"

    t = title
    num = _CARD_NUMBER_PATTERN.search(t)
    if num:
        t = t[: num.start()].strip()

    # Remove trailing set codes like 'Swsh08:' or 'SV3:' if they appear at the end of the left segment
    t = re.sub(r"\b(SWSH|SV)\s*\d{1,2}\b[:\-]?\s*$", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"\b(SWSH|SV)\d{1,2}\b[:\-]?\s*$", "", t, flags=re.IGNORECASE).strip()

    # Strip punctuation chunks
    t = re.sub(r"[\-\|•]+", " ", t)
    t = re.sub(r"\([^)]*\)", " ", t)

    # Remove common noise tokens
    t = _NOISE_TOKENS.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip()

    # Keep first ~4 tokens to avoid long titles becoming "names"
    parts = t.split()
    if not parts:
        return "Unknown"
    return " ".join(parts[:4])


def parse_set_from_title(title: str) -> str:
    """Extract set name from title (substring match from known list), else 'Unknown Set'."""
    if not title or not isinstance(title, str):
        return "Unknown Set"
    t = title
    for name in KNOWN_SET_SUBSTRINGS:
        if name.lower() in t.lower():
            return name
    # Try pattern like "123/456" and take preceding word(s) as set hint
    m = re.search(r"(\d+/\d+)\s*$", t)
    if m:
        before = t[: m.start()].strip()
        if before:
            parts = before.split()
            if len(parts) >= 2:
                return parts[-2] + " " + parts[-1]
    return "Unknown Set"


def parse_set_and_card_slugs(title: str) -> Tuple[str, str]:
    """
    Return (set_slug, card_slug) for use in canonical card_id.
    set_slug from parse_set_from_title.
    card_slug from (card_name + card_number) when possible, else slugified title.
    """
    set_name = parse_set_from_title(title)
    set_slug = slugify(set_name, max_len=60)
    if not set_slug:
        set_slug = "unknown-set"
    card_name = parse_card_name(title)
    card_number = parse_card_number(title)
    if card_number:
        card_slug = slugify(f"{card_name} {card_number}", max_len=80)
    else:
        card_slug = slugify(card_name, max_len=80) or slugify(title, max_len=80)
    if not card_slug:
        card_slug = "unknown"
    return set_slug, card_slug

# Language: Japanese indicators in title (else treated as English; anything else = other)
_JAPANESE_PATTERNS = re.compile(
    r"\b(Japanese|Japan|JPN|Jp\b|Japanese language)\b",
    re.IGNORECASE,
)

# Grading: company abbreviation followed by optional space and grade number (e.g. PSA 10, BGS 9.5)
# Order matters: longer names first so we don't match "Jp" inside "Japanese"
_GRADE_PATTERN = re.compile(
    r"\b(PSA|BGS|CGC|SGC|TAG|ACE)\s*(\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)


def parse_language(title: str) -> str:
    """
    Return 'jp', 'en', or 'other'.
    Only Japanese and English are explicitly detected; all others (e.g. Korean, French) = 'other'.
    """
    if not title or not isinstance(title, str):
        return "other"
    if _JAPANESE_PATTERNS.search(title):
        return "jp"
    # Default to English for Pokémon US market; non-JP/non-EN can be set to 'other' by caller if needed
    return "en"


def parse_grade(title: str) -> Tuple[Optional[str], Optional[float]]:
    """
    Extract (grade_company, grade_value) from title, or (None, None) for raw.
    Uses first match if multiple (e.g. "PSA 10 BGS 9" -> PSA, 10).
    """
    if not title or not isinstance(title, str):
        return None, None
    m = _GRADE_PATTERN.search(title)
    if not m:
        return None, None
    company = m.group(1).upper()
    # "Jp" is not a grading company; avoid matching substring of "Japanese"
    if company == "JP":
        return None, None
    try:
        value = float(m.group(2))
    except (ValueError, TypeError):
        return None, None
    # Normalize company names
    if company not in ("PSA", "BGS", "CGC", "SGC", "TAG", "ACE"):
        return None, None
    return company, value
