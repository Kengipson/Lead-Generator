"""
Turn raw Apify Google Maps Scraper dataset items into clean lead records,
flag high-priority (no-website) leads, and export to CSV.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

# Column order for the exported CSV.
CSV_FIELDS = [
    "name",
    "phone",
    "website",
    "rating",
    "review_count",
    "category",
    "address",
    "high_priority_no_website",
    "google_maps_url",
]


def normalize_lead(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract and clean the fields we care about from one raw actor result.

    The compass/crawler-google-places actor returns a lot of fields per
    place; we only keep what's useful for outreach. A missing/blank website
    flags the lead as high priority (no web presence = easier pitch, more
    likely to need help).
    """
    website = (raw.get("website") or "").strip()
    phone = (raw.get("phone") or raw.get("phoneUnformatted") or "").strip()
    name = (raw.get("title") or raw.get("name") or "").strip()
    category = (raw.get("categoryName") or raw.get("category") or "").strip()
    address = (raw.get("address") or "").strip()

    rating = raw.get("totalScore")
    review_count = raw.get("reviewsCount")

    return {
        "name": name,
        "phone": phone,
        "website": website,
        "rating": rating if rating is not None else "",
        "review_count": review_count if review_count is not None else "",
        "category": category,
        "address": address,
        "high_priority_no_website": not website,
        "google_maps_url": raw.get("url") or raw.get("searchPageUrl") or "",
    }


def normalize_leads(raw_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize a whole batch of raw actor results."""
    return [normalize_lead(item) for item in raw_results]


def export_to_csv(leads: list[dict[str, Any]], output_path: str | Path) -> Path:
    """Write normalized leads to a clean CSV, high-priority (no-website) leads first."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # High-priority leads (no website) surface at the top of the file.
    sorted_leads = sorted(
        leads, key=lambda lead: not lead["high_priority_no_website"]
    )

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for lead in sorted_leads:
            row = {field: lead.get(field, "") for field in CSV_FIELDS}
            # Write a friendly Yes/No instead of True/False in the CSV.
            row["high_priority_no_website"] = "Yes" if row["high_priority_no_website"] else "No"
            writer.writerow(row)

    return output_path
