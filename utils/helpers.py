"""
utils/helpers.py — Shared utility functions for the Google Maps Scraper.

Provides: logging setup, human-like delays, data cleaning, export writers,
           stealth injection, and deduplication helpers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from config import (
    EXPORT_FORMAT,
    LOG_LEVEL,
    OUTPUT_DIR,
    RANDOM_DELAY_MAX,
    RANDOM_DELAY_MIN,
)

console = Console()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logger(name: str = "gmaps_scraper") -> logging.Logger:
    """Return a Rich-powered logger for the project."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        show_path=False,
        markup=True,
    )
    handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    logger.addHandler(handler)
    return logger


log = setup_logger()

# ---------------------------------------------------------------------------
# Human-like random delays
# ---------------------------------------------------------------------------

async def human_delay(
    min_s: float = RANDOM_DELAY_MIN,
    max_s: float = RANDOM_DELAY_MAX,
) -> None:
    """Sleep for a random duration to mimic human browsing."""
    delay = random.uniform(min_s, max_s)
    log.debug(f"Sleeping {delay:.2f}s")
    await asyncio.sleep(delay)


async def random_scroll(page: Any) -> None:
    """Perform a small random scroll to simulate human behaviour."""
    distance = random.randint(100, 400)
    await page.mouse.wheel(0, distance)
    await human_delay(0.3, 0.8)

# ---------------------------------------------------------------------------
# Text / data cleaning
# ---------------------------------------------------------------------------

def clean_text(raw: str | None) -> str:
    """Strip whitespace, zero-width chars, and normalize unicode."""
    if not raw:
        return ""
    text = raw.strip()
    # Remove zero-width characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    return text


def extract_number(text: str | None) -> int | None:
    """Pull the first integer from a string like '(1,234 reviews)'."""
    if not text:
        return None
    nums = re.findall(r"[\d,]+", text)
    if not nums:
        return None
    return int(nums[0].replace(",", ""))


def extract_rating(text: str | None) -> float | None:
    """Extract a float rating like '4.5' from text."""
    if not text:
        return None
    match = re.search(r"\d+\.?\d*", text)
    return float(match.group()) if match else None

# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(records: list[dict]) -> list[dict]:
    """Remove duplicate leads by (business_name + address) key."""
    seen: set[str] = set()
    unique: list[dict] = []
    for rec in records:
        key = f"{rec.get('business_name', '')}|{rec.get('address', '')}".lower()
        if key not in seen:
            seen.add(key)
            unique.append(rec)
    log.info(f"Deduplicated {len(records)} → {len(unique)} records")
    return unique

# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def _ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def _timestamp_filename(prefix: str, ext: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return _ensure_output_dir() / f"{prefix}_{ts}.{ext}"


def export_to_csv(data: list[dict], prefix: str = "leads") -> Path:
    """Write leads to a timestamped CSV file."""
    path = _timestamp_filename(prefix, "csv")
    df = pd.DataFrame(data)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info(f"[green]✔ Exported {len(data)} leads → {path}[/green]")
    return path


def export_to_xlsx(data: list[dict], prefix: str = "leads") -> Path:
    """Write leads to a timestamped Excel file with auto-column-width."""
    path = _timestamp_filename(prefix, "xlsx")
    df = pd.DataFrame(data)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Leads")
        ws = writer.sheets["Leads"]
        for i, col in enumerate(df.columns, 1):
            max_len = max(
                df[col].astype(str).map(len).max(),
                len(col),
            ) + 3
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = min(max_len, 50)
    log.info(f"[green]✔ Exported {len(data)} leads → {path}[/green]")
    return path


def export_to_json(data: list[dict], prefix: str = "leads") -> Path:
    """Write leads to a timestamped JSON file."""
    path = _timestamp_filename(prefix, "json")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"[green]✔ Exported {len(data)} leads → {path}[/green]")
    return path


def export_data(data: list[dict], fmt: str | None = None, prefix: str = "leads") -> Path:
    """Dispatch to the correct exporter based on config or override."""
    fmt = (fmt or EXPORT_FORMAT).lower()
    exporters = {
        "csv": export_to_csv,
        "xlsx": export_to_xlsx,
        "json": export_to_json,
    }
    exporter = exporters.get(fmt)
    if exporter is None:
        log.warning(f"Unknown format '{fmt}', falling back to CSV")
        exporter = export_to_csv
    return exporter(data, prefix)

# ---------------------------------------------------------------------------
# Stealth injection (bypass basic bot-detection)
# ---------------------------------------------------------------------------

STEALTH_JS = """
// Override navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// Override chrome runtime
window.chrome = { runtime: {} };

// Override permissions query
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({state: Notification.permission})
        : originalQuery(parameters);

// Override plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Override languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

// Spoof platform
Object.defineProperty(navigator, 'platform', {
    get: () => 'Win32',
});
"""


async def inject_stealth(page: Any) -> None:
    """Inject anti-detection JavaScript into a Playwright page."""
    await page.add_init_script(STEALTH_JS)
    log.debug("Stealth scripts injected")

# ---------------------------------------------------------------------------
# Rich progress bar factory
# ---------------------------------------------------------------------------

def create_progress() -> Progress:
    """Return a pre-configured Rich progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )
