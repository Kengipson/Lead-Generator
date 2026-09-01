# Lead Generator

Finds local service businesses on Google Maps (e.g. "roofers in Atlanta, GA")
using the Apify Google Maps Scraper actor, flags no-website businesses as
high-priority leads, and exports everything to CSV -- with an optional
auto-append into an existing outreach-tracker spreadsheet.

## Status

- [x] Project scaffolding + raw Apify pull
- [x] Extract/normalize fields: name, phone, website, rating, review count, category
- [x] Flag businesses with no website as high-priority leads
- [x] Export clean CSV
- [x] Optional: append new leads into an outreach-tracker `.xlsx`
- [x] Optional: create a personalized Gmail draft for each new lead

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

   Optionally also set `OUTREACH_TRACKER_PATH` -- see
   [Outreach tracker](#outreach-tracker-optional) below.

## Usage

```bash
python main.py --industry "roofers" --location "Atlanta, GA"
```

Options:

- `--industry` (required) - type of business, e.g. `"roofers"`
- `--location` (required) - city/region, e.g. `"Atlanta, GA"`
- `--max-results` (optional, default 50) - max businesses to pull
- `--output` (optional) - custom path for the raw JSON output
- `--csv-output` (optional) - custom path for the clean leads CSV
- `--tracker-path` (optional) - path to an outreach-tracker `.xlsx`; overrides `OUTREACH_TRACKER_PATH`
- `--skip-tracker` (optional) - skip the tracker update for this run
- `--gmail-credentials-path` (optional) - path to a Google OAuth `credentials.json`; overrides `GMAIL_CREDENTIALS_PATH`
- `--gmail-token-path` (optional) - where to cache the Gmail OAuth token; overrides `GMAIL_TOKEN_PATH`
- `--skip-drafts` (optional) - skip Gmail draft creation for this run

This runs the [Google Maps Scraper](https://apify.com/compass/crawler-google-places)
actor on Apify with the search query `"<industry> in <location>"` and writes,
under `output/`:

- `raw_<slug>_<timestamp>.json` - untouched dataset items exactly as the actor returns them
- `leads_<slug>_<timestamp>.csv` - cleaned, normalized leads, no-website ones flagged and sorted first

## Outreach tracker (optional)

If `OUTREACH_TRACKER_PATH` is set in `.env` (or `--tracker-path` is passed) to
an `.xlsx` file with an "Outreach Tracker" sheet, each run also appends new
leads as rows in that sheet -- in addition to the CSV, which is always
written. A lead is skipped as a duplicate if its business name or phone
number (digits only) already appears anywhere in the sheet.

Column mapping:

| Tracker column | Value |
|---|---|
| Business Name | lead name |
| Industry | the `--industry` you searched |
| Contact Name | left blank |
| Phone / Email | lead phone |
| Website | lead website URL, or `"NO WEBSITE"` if none -- the key lead-priority signal |
| Source | `"Google Maps"` |
| Date Contacted | left blank |
| Free Sample Sent?, Sample Sent Date, Response, Follow-Up Date | left blank |
| Status | `"New Lead"` |
| Notes | `"Found via Maps search - <industry> in <location>"`, plus a no-website flag if applicable |

Use `--skip-tracker` to skip this step for a single run even if a tracker
path is configured.

## Gmail drafts (optional)

If `GMAIL_CREDENTIALS_PATH` is set in `.env` (or `--gmail-credentials-path`
is passed) to a Google OAuth "installed app" `credentials.json`, each run
creates a Gmail draft for every *newly added* tracker row (duplicates and
leads that failed to append are skipped). The draft has no recipient set --
Google Maps doesn't return emails, so fill in "To" by hand before sending.
Once a draft is created, that lead's tracker Status is updated to
`"Draft Ready"` so you know which ones are waiting on you to review and send.

Setup:

1. In [Google Cloud Console](https://console.cloud.google.com/apis/credentials),
   enable the Gmail API and create an OAuth client ID of type "Desktop app".
   Download it and point `GMAIL_CREDENTIALS_PATH` at the file.
2. First run opens a browser to sign in and authorize; the token is then
   cached (default `token.json` next to `main.py`, or `GMAIL_TOKEN_PATH`) so
   later runs don't prompt again.

**Never commit `credentials.json` or the cached token file** -- both are
already gitignored. The Gmail scope used is `gmail.compose`, which can only
create/edit drafts, not read or send existing mail.

Email template (business name substituted in both places):

> Subject: A free AI video ad for [Business Name]
>
> Hey there — I'm Ken AI Solutions here in Metro Atlanta. I make short AI
> video ads for small businesses, and I actually already built you a free
> one using [Business Name]'s website — no charge, no catch.
>
> Want me to send it over? Takes 30 seconds to watch. If you like it,
> great — if not, no hard feelings either way.

Use `--skip-drafts` to skip this step for a single run even if Gmail
credentials are configured.

## Project structure

```
.
├── main.py                    # CLI entry point
├── src/
│   ├── apify_scraper.py       # Apify API wrapper (search + fetch raw results)
│   ├── leads.py                # Normalize raw results, flag no-website leads, export CSV
│   ├── outreach_tracker.py    # Append new leads into an outreach-tracker .xlsx, deduped
│   └── gmail_drafts.py        # Create a Gmail draft per new lead via OAuth
├── requirements.txt
├── .env.example
├── credentials.json           # Google OAuth client secret (gitignored, not included)
├── token.json                 # Cached Gmail OAuth token (gitignored, created on first run)
└── output/                    # raw JSON + CSV results land here (gitignored)
```
