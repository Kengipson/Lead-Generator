#!/usr/bin/env python3
"""
Lead Generator - pulls local service businesses from Google Maps via Apify,
flags no-website businesses as high-priority leads, and exports a clean CSV.

Usage:
    python main.py --industry "roofers" --location "Atlanta, GA"
    python main.py --industry "plumbers" --location "Denver, CO" --max-results 100

Writes two files to output/:
  - raw_<slug>_<timestamp>.json  - untouched results straight from Apify
  - leads_<slug>_<timestamp>.csv - cleaned, flagged, ready-to-work leads
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.apify_scraper import ApifyConfigError, fetch_raw_leads
from src.leads import export_to_csv, normalize_leads

OUTPUT_DIR = Path(__file__).parent / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pull raw local-business leads from Google Maps via Apify."
    )
    parser.add_argument(
        "--industry",
        required=True,
        help='Type of business to search for, e.g. "roofers"',
    )
    parser.add_argument(
        "--location",
        required=True,
        help='Where to search, e.g. "Atlanta, GA"',
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Max number of businesses to pull (default: 50)",
    )
    parser.add_argument(
        "--output",
        help="Path to write the raw JSON results (default: output/raw_<slug>_<timestamp>.json)",
    )
    parser.add_argument(
        "--csv-output",
        help="Path to write the clean leads CSV (default: output/leads_<slug>_<timestamp>.csv)",
    )
    return parser.parse_args()


def slugify(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in text).strip("_")


def main() -> int:
    load_dotenv()
    args = parse_args()

    try:
        print(f'Fetching up to {args.max_results} results for "{args.industry} in {args.location}"...')
        results = fetch_raw_leads(
            industry=args.industry,
            location=args.location,
            max_results=args.max_results,
        )
    except ApifyConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Failed to fetch leads: {e}", file=sys.stderr)
        return 1

    print(f"Got {len(results)} raw results.")

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = f"{slugify(args.industry)}_{slugify(args.location)}"

    output_path = Path(args.output) if args.output else OUTPUT_DIR / f"raw_{slug}_{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Raw results written to {output_path}")

    leads = normalize_leads(results)
    high_priority_count = sum(1 for lead in leads if lead["high_priority_no_website"])
    print(f"{high_priority_count} of {len(leads)} leads have no website (flagged high-priority).")

    csv_path = Path(args.csv_output) if args.csv_output else OUTPUT_DIR / f"leads_{slug}_{timestamp}.csv"
    export_to_csv(leads, csv_path)
    print(f"Clean leads CSV written to {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
