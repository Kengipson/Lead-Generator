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
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.apify_scraper import ApifyConfigError, fetch_raw_leads
from src.gmail_drafts import create_draft, get_gmail_service
from src.leads import export_to_csv, normalize_leads
from src.outreach_tracker import append_leads_to_tracker, mark_status

OUTPUT_DIR = Path(__file__).parent / "output"
DEFAULT_GMAIL_TOKEN_PATH = Path(__file__).parent / "token.json"


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
    parser.add_argument(
        "--tracker-path",
        help=(
            "Path to an outreach-tracker .xlsx with an 'Outreach Tracker' sheet "
            "to append new leads into. Falls back to the OUTREACH_TRACKER_PATH "
            "env var / .env entry. If neither is set, the tracker step is skipped."
        ),
    )
    parser.add_argument(
        "--skip-tracker",
        action="store_true",
        help="Skip appending leads to the outreach tracker even if a path is configured.",
    )
    parser.add_argument(
        "--gmail-credentials-path",
        help=(
            "Path to a Google OAuth 'installed app' credentials.json to create Gmail "
            "drafts for new leads. Falls back to the GMAIL_CREDENTIALS_PATH env var / "
            ".env entry. If neither is set, the draft step is skipped."
        ),
    )
    parser.add_argument(
        "--gmail-token-path",
        help=(
            "Path to cache the Gmail OAuth token after the first authorization "
            "(default: token.json next to main.py). Falls back to GMAIL_TOKEN_PATH."
        ),
    )
    parser.add_argument(
        "--skip-drafts",
        action="store_true",
        help="Skip creating Gmail drafts for new leads even if credentials are configured.",
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

    tracker_path = args.tracker_path or os.environ.get("OUTREACH_TRACKER_PATH")
    appended_rows: list[dict] = []
    if args.skip_tracker:
        print("Skipping outreach tracker update (--skip-tracker).")
    elif not tracker_path:
        print(
            "No outreach tracker configured (set --tracker-path or "
            "OUTREACH_TRACKER_PATH in .env) -- skipping tracker update."
        )
    else:
        try:
            summary = append_leads_to_tracker(
                leads, industry=args.industry, location=args.location, tracker_path=tracker_path
            )
            appended_rows = summary["appended_rows"]
            print(
                f"Outreach tracker updated: {summary['appended']} new lead(s) added, "
                f"{summary['skipped_duplicates']} duplicate(s) skipped."
            )
        except Exception as e:
            print(f"Warning: failed to update outreach tracker: {e}", file=sys.stderr)

    gmail_credentials_path = args.gmail_credentials_path or os.environ.get("GMAIL_CREDENTIALS_PATH")
    gmail_token_path = args.gmail_token_path or os.environ.get("GMAIL_TOKEN_PATH") or DEFAULT_GMAIL_TOKEN_PATH
    if args.skip_drafts:
        print("Skipping Gmail draft creation (--skip-drafts).")
    elif not appended_rows:
        print("No new leads to draft emails for.")
    elif not gmail_credentials_path:
        print(
            "No Gmail credentials configured (set --gmail-credentials-path or "
            "GMAIL_CREDENTIALS_PATH in .env) -- skipping draft creation."
        )
    else:
        try:
            service = get_gmail_service(gmail_credentials_path, gmail_token_path)
            drafted_rows: dict[int, str] = {}
            for entry in appended_rows:
                name = entry["lead"]["name"]
                try:
                    create_draft(service, name)
                    drafted_rows[entry["row"]] = "Draft Ready"
                except Exception as e:
                    print(f"Warning: failed to create draft for {name!r}: {e}", file=sys.stderr)

            if drafted_rows:
                mark_status(tracker_path, drafted_rows)
            print(
                f"Created {len(drafted_rows)} of {len(appended_rows)} Gmail draft(s); "
                f"marked as Draft Ready in the tracker."
            )
        except Exception as e:
            print(f"Warning: failed to create Gmail drafts: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
