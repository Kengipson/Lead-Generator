"""
Thin wrapper around the Apify Google Maps Scraper actor.

Given an industry (e.g. "roofers") and a location (e.g. "Atlanta, GA"), this
module runs the actor via the Apify API and returns the raw dataset items it
produced -- no filtering, scoring, or CSV export yet. Those come next.
"""

from __future__ import annotations

import os
from typing import Any

from apify_client import ApifyClient

# Default actor: "Google Maps Scraper" by compass (a.k.a. crawler-google-places).
# https://apify.com/compass/crawler-google-places
DEFAULT_ACTOR_ID = "compass/crawler-google-places"


class ApifyConfigError(RuntimeError):
    """Raised when required Apify configuration (e.g. the API token) is missing."""


def build_search_query(industry: str, location: str) -> str:
    """Combine industry + location into the search string Google Maps expects.

    e.g. build_search_query("roofers", "Atlanta, GA") -> "roofers in Atlanta, GA"
    """
    industry = industry.strip()
    location = location.strip()
    if not industry:
        raise ValueError("industry must not be empty")
    if not location:
        raise ValueError("location must not be empty")
    return f"{industry} in {location}"


def fetch_raw_leads(
    industry: str,
    location: str,
    max_results: int = 50,
    api_token: str | None = None,
    actor_id: str | None = None,
) -> list[dict[str, Any]]:
    """Run the Apify Google Maps Scraper actor and return the raw dataset items.

    Args:
        industry: The type of business to search for, e.g. "roofers".
        location: Where to search, e.g. "Atlanta, GA".
        max_results: Max number of places the actor should crawl.
        api_token: Apify API token. Falls back to the APIFY_API_TOKEN env var.
        actor_id: Apify actor to call. Falls back to APIFY_ACTOR_ID env var,
            then DEFAULT_ACTOR_ID.

    Returns:
        A list of raw place records exactly as returned by the actor's
        dataset (one dict per business found).
    """
    api_token = api_token or os.environ.get("APIFY_API_TOKEN")
    if not api_token:
        raise ApifyConfigError(
            "No Apify API token found. Set APIFY_API_TOKEN in your environment "
            "or .env file, or pass api_token explicitly."
        )

    actor_id = actor_id or os.environ.get("APIFY_ACTOR_ID") or DEFAULT_ACTOR_ID

    search_query = build_search_query(industry, location)

    run_input = {
        "searchStringsArray": [search_query],
        "maxCrawledPlacesPerSearch": max_results,
        "language": "en",
        "skipClosedPlaces": False,
    }

    client = ApifyClient(api_token)

    run = client.actor(actor_id).call(run_input=run_input)

    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        raise RuntimeError(
            f"Actor run finished but returned no dataset id. Run info: {run}"
        )

    items: list[dict[str, Any]] = []
    for item in client.dataset(dataset_id).iterate_items():
        items.append(item)

    return items
