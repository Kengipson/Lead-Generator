"""
Create personalized Gmail drafts (no recipient set) for new leads, using a
Google OAuth "installed app" client.

First run opens a browser for the user to sign in and authorize; the
resulting token is cached to disk so later runs don't prompt again (until it
expires or is revoked).

Scope is deliberately limited to gmail.compose -- enough to create drafts,
not to read or send existing mail.
"""

from __future__ import annotations

import base64
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

SUBJECT_TEMPLATE = "A free AI video ad for {business_name}"

BODY_TEMPLATE = (
    "Hey there — I'm Ken AI Solutions here in Metro Atlanta. I make short AI "
    "video ads for small businesses, and I actually already built you a free "
    "one using {business_name}'s website — no charge, no catch.\n\n"
    "Want me to send it over? Takes 30 seconds to watch. If you like it, "
    "great — if not, no hard feelings either way."
)


def build_email_content(business_name: str) -> tuple[str, str]:
    """Return (subject, body) for a lead's outreach email."""
    subject = SUBJECT_TEMPLATE.format(business_name=business_name)
    body = BODY_TEMPLATE.format(business_name=business_name)
    return subject, body


def get_gmail_service(credentials_path: str | Path, token_path: str | Path):
    """Return an authorized Gmail API service, running the OAuth consent
    flow (opens a browser) on first use and caching the token afterward."""
    credentials_path = Path(credentials_path)
    token_path = Path(token_path)

    if not credentials_path.exists():
        raise FileNotFoundError(f"Gmail OAuth credentials file not found: {credentials_path}")

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def _build_draft_body(business_name: str) -> dict[str, Any]:
    subject, body = build_email_content(business_name)
    message = MIMEText(body)
    message["Subject"] = subject
    # "To" is intentionally left unset -- Google Maps doesn't return emails,
    # so the recipient gets filled in by hand before sending.
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"message": {"raw": raw}}


def create_draft(service, business_name: str, user_id: str = "me") -> str:
    """Create a Gmail draft for one lead and return its draft id."""
    draft = service.users().drafts().create(userId=user_id, body=_build_draft_body(business_name)).execute()
    return draft["id"]
