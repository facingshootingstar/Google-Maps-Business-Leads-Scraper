"""
config.py — Centralized configuration for Google Maps Business Leads Scraper.

Loads settings from .env and exposes typed, validated config constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _bool(val: str | None, default: bool = False) -> bool:
    """Convert an env-var string to a Python bool."""
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes")


def _int(val: str | None, default: int = 0) -> int:
    try:
        return int(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _float(val: str | None, default: float = 0.0) -> float:
    try:
        return float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
SEARCH_QUERY: str = os.getenv("SEARCH_QUERY", "restaurants in New York")
MAX_RESULTS: int = _int(os.getenv("MAX_RESULTS"), 100)

# ---------------------------------------------------------------------------
# Browser / Playwright
# ---------------------------------------------------------------------------
HEADLESS: bool = _bool(os.getenv("HEADLESS"), True)
SLOW_MO: int = _int(os.getenv("SLOW_MO"), 50)
BROWSER_TIMEOUT: int = _int(os.getenv("BROWSER_TIMEOUT"), 60_000)

# ---------------------------------------------------------------------------
# Anti-detection
# ---------------------------------------------------------------------------
USE_STEALTH: bool = _bool(os.getenv("USE_STEALTH"), True)
RANDOM_DELAY_MIN: float = _float(os.getenv("RANDOM_DELAY_MIN"), 1.5)
RANDOM_DELAY_MAX: float = _float(os.getenv("RANDOM_DELAY_MAX"), 4.0)

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
EXPORT_FORMAT: str = os.getenv("EXPORT_FORMAT", "csv").lower()
OUTPUT_DIR: Path = BASE_DIR / os.getenv("OUTPUT_DIR", "output")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

# ---------------------------------------------------------------------------
# Proxy (optional)
# ---------------------------------------------------------------------------
PROXY_SERVER: str | None = os.getenv("PROXY_SERVER")

# ---------------------------------------------------------------------------
# Google Maps selectors (2025-2026 DOM structure)
# ---------------------------------------------------------------------------
SELECTORS = {
    "search_box": "#searchboxinput",
    "search_button": "#searchbox-searchbutton",
    "result_feed": "div[role='feed']",
    "result_item": "div[role='feed'] > div > div > a",
    "business_name": "h1.DUwDvf",
    "rating": "div.F7nice span[aria-hidden='true']",
    "reviews_count": "span[aria-label*='reviews']",
    "category": "button.DkEaL",
    "address": "button[data-item-id='address'] div.Io6YTe",
    "phone": "button[data-item-id*='phone'] div.Io6YTe",
    "website": "a[data-item-id='authority'] div.Io6YTe",
    "plus_code": "button[data-item-id='oloc'] div.Io6YTe",
    "hours": "div.t39EBf.GUrTXd",
}

# ---------------------------------------------------------------------------
# Viewport & locale fingerprinting
# ---------------------------------------------------------------------------
VIEWPORT = {"width": 1920, "height": 1080}
LOCALE = "en-US"
TIMEZONE = "America/New_York"
GEOLOCATION = None  # Set to {"latitude": x, "longitude": y} if needed
