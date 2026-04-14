"""
main.py — CLI entry-point for Google Maps Business Leads Scraper.

Provides a rich interactive CLI with support for:
  • Single query scraping
  • Batch mode (multiple queries from a file)
  • Multiple export formats (CSV / XLSX / JSON)
  • Real-time progress tracking
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from config import EXPORT_FORMAT, MAX_RESULTS, SEARCH_QUERY
from scraper import GoogleMapsScraper
from utils.helpers import (
    console,
    create_progress,
    deduplicate,
    export_data,
    log,
)

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

BANNER = r"""
   ██████╗ ███╗   ███╗ █████╗ ██████╗ ███████╗
  ██╔════╝ ████╗ ████║██╔══██╗██╔══██╗██╔════╝
  ██║  ███╗██╔████╔██║███████║██████╔╝███████╗
  ██║   ██║██║╚██╔╝██║██╔══██║██╔═══╝ ╚════██║
  ╚██████╔╝██║ ╚═╝ ██║██║  ██║██║     ███████║
   ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝
  Google Maps Business Leads Scraper  v2.0.0
"""

# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape business leads from Google Maps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
        "  python main.py -q 'dentists in Miami'\n"
        "  python main.py -q 'gyms in LA' -n 50 -f xlsx\n"
        "  python main.py --batch queries.txt -f json\n"
        "  python main.py -q 'hotels in Paris' --no-headless\n",
    )
    parser.add_argument(
        "-q", "--query",
        type=str,
        default=SEARCH_QUERY,
        help="Search query (default from .env)",
    )
    parser.add_argument(
        "-n", "--max-results",
        type=int,
        default=MAX_RESULTS,
        help="Max number of results to scrape (default from .env)",
    )
    parser.add_argument(
        "-f", "--format",
        type=str,
        default=EXPORT_FORMAT,
        choices=["csv", "xlsx", "json"],
        help="Export format (default from .env)",
    )
    parser.add_argument(
        "--batch",
        type=str,
        default=None,
        help="Path to a text file with one search query per line",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible (headed) mode",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Skip deduplication of results",
    )
    return parser

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def show_banner() -> None:
    console.print(Panel(BANNER, border_style="bright_blue", expand=False))


def show_summary_table(leads: list[dict], export_path: Path) -> None:
    """Print a quick summary table of the first N results."""
    table = Table(
        title="📊 Scrape Summary",
        show_lines=True,
        header_style="bold magenta",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Business Name", style="cyan", max_width=30)
    table.add_column("Phone", style="green")
    table.add_column("Rating", justify="center")
    table.add_column("Reviews", justify="right")
    table.add_column("Category", style="yellow", max_width=20)

    for i, lead in enumerate(leads[:15], 1):
        table.add_row(
            str(i),
            lead.get("business_name", "—"),
            lead.get("phone", "—") or "—",
            str(lead.get("rating", "—")),
            str(lead.get("reviews_count", "—")),
            lead.get("category", "—") or "—",
        )

    if len(leads) > 15:
        table.add_row("…", f"+ {len(leads) - 15} more", "", "", "", "")

    console.print(table)
    console.print(
        f"\n[bold green]✅ {len(leads)} leads exported →[/bold green] "
        f"[underline]{export_path}[/underline]\n"
    )

# ---------------------------------------------------------------------------
# Core run logic
# ---------------------------------------------------------------------------

async def scrape_query(
    query: str,
    max_results: int,
    headless: bool,
    fmt: str,
    dedup: bool = True,
) -> list[dict]:
    """Scrape a single query and export results."""
    async with GoogleMapsScraper(
        search_query=query,
        max_results=max_results,
        headless=headless,
    ) as scraper:
        leads = await scraper.scrape()

    if dedup:
        leads = deduplicate(leads)

    if leads:
        # Build a safe file prefix from the query
        prefix = query.lower().replace(" ", "_")[:40]
        path = export_data(leads, fmt=fmt, prefix=prefix)
        show_summary_table(leads, path)
    else:
        console.print("[bold red]No leads found for this query.[/bold red]")

    return leads


async def run_batch(
    batch_file: str,
    max_results: int,
    headless: bool,
    fmt: str,
    dedup: bool = True,
) -> None:
    """Read queries from a file and scrape each one sequentially."""
    queries = Path(batch_file).read_text(encoding="utf-8").strip().splitlines()
    queries = [q.strip() for q in queries if q.strip() and not q.startswith("#")]

    console.print(f"[bold]Batch mode:[/bold] {len(queries)} queries loaded from {batch_file}")

    all_leads: list[dict] = []

    for idx, query in enumerate(queries, 1):
        console.rule(f"[bold cyan]Query {idx}/{len(queries)}: {query}[/bold cyan]")
        leads = await scrape_query(query, max_results, headless, fmt, dedup)
        all_leads.extend(leads)
        if idx < len(queries):
            log.info("Cooling down before next query …")
            import random
            await asyncio.sleep(random.uniform(5.0, 12.0))

    console.print(
        f"\n[bold green]🎉 Batch complete — {len(all_leads)} total leads across "
        f"{len(queries)} queries[/bold green]"
    )

# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    show_banner()

    headless = not args.no_headless
    dedup = not args.no_dedup

    console.print(f"[dim]Query:[/dim]        {args.query}")
    console.print(f"[dim]Max results:[/dim]  {args.max_results}")
    console.print(f"[dim]Format:[/dim]       {args.format}")
    console.print(f"[dim]Headless:[/dim]     {headless}")
    console.print()

    try:
        if args.batch:
            asyncio.run(run_batch(args.batch, args.max_results, headless, args.format, dedup))
        else:
            asyncio.run(scrape_query(args.query, args.max_results, headless, args.format, dedup))
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠ Interrupted by user[/bold yellow]")
        sys.exit(1)
    except Exception as exc:
        log.exception(f"Fatal error: {exc}")
        sys.exit(2)


if __name__ == "__main__":
    main()
