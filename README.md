# Lead Generator

Finds local service businesses on Google Maps (e.g. "roofers in Atlanta, GA")
using the Apify Google Maps Scraper actor, and will eventually flag
no-website businesses as high-priority leads and export everything to CSV.

## Status

**Step 1 (this commit):** project scaffolding + a script that takes an
industry and location, calls the Apify actor, and dumps the raw results to
JSON. No filtering, scoring, or CSV export yet -- that's next.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your Apify API token:

   ```bash
   cp .env.example .env
   ```

   ```
   APIFY_API_TOKEN=your_apify_token_here
   ```

   Get a token from https://console.apify.com/account/integrations.

## Usage

```bash
python main.py --industry "roofers" --location "Atlanta, GA"
```

Options:

- `--industry` (required) - type of business, e.g. `"roofers"`
- `--location` (required) - city/region, e.g. `"Atlanta, GA"`
- `--max-results` (optional, default 50) - max businesses to pull
- `--output` (optional) - custom path for the raw JSON output

This runs the [Google Maps Scraper](https://apify.com/compass/crawler-google-places)
actor on Apify with the search query `"<industry> in <location>"` and writes
the raw dataset items (one JSON object per business, exactly as the actor
returns them) to `output/raw_<industry>_<location>_<timestamp>.json`.

## Project structure

```
.
├── main.py                 # CLI entry point
├── src/
│   └── apify_scraper.py    # Apify API wrapper (search + fetch raw results)
├── requirements.txt
├── .env.example
└── output/                 # raw JSON results land here (gitignored)
```

## Roadmap

- [x] Project scaffolding + raw Apify pull
- [ ] Extract/normalize fields: name, phone, website, rating, review count, category
- [ ] Flag businesses with no website as high-priority leads
- [ ] Export clean CSV
