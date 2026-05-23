"""
Triggers the Month 2 referral email for active clients.
Run as a scheduled job at the start of month 2 post-onboarding.

Usage:
  python referral_email.py           # check all clients, trigger where due
  python referral_email.py --dry-run # print who would be triggered
"""
import argparse
import datetime
import json
import os

import requests
from dotenv import load_dotenv
import airtable_client as db

load_dotenv()

INSTANTLY_API = "https://api.instantly.ai/api/v1"
REFERRAL_CAMPAIGN_ID = os.environ.get("INSTANTLY_REFERRAL_CAMPAIGN_ID", "")


def check_and_trigger(dry_run: bool = False) -> list[str]:
    """
    For every onboarded client whose onboarded_at is 28-35 days ago
    and who hasn't received the referral email yet, fire the sequence.
    Returns list of triggered client names.
    """
    base = db._get_base()
    client_records = base.table("Clients").all(
        formula="NOT({referral_email_sent})"
    )

    triggered = []
    now = datetime.datetime.utcnow()

    for record in client_records:
        fields = record["fields"]
        onboarded_str = fields.get("onboarded_at")
        if not onboarded_str:
            continue

        onboarded = datetime.datetime.fromisoformat(onboarded_str.replace("Z", "+00:00"))
        onboarded = onboarded.replace(tzinfo=None)
        days_since = (now - onboarded).days

        if days_since < 28 or days_since > 60:
            continue

        # pull lead for email + name
        lead_ids = fields.get("lead_id", [])
        if not lead_ids:
            continue

        lead_records = base.table("Leads").all(
            formula=f"RECORD_ID() = '{lead_ids[0]}'"
        )
        if not lead_records:
            continue

        lead = {"id": lead_records[0]["id"], **lead_records[0]["fields"]}
        name = lead.get("name", "")
        email = lead.get("email", "")

        print(f"[referral] {'(dry-run) ' if dry_run else ''}triggering for {name} — day {days_since}")

        if not dry_run:
            _activate_referral_sequence(email, name, days_since, record["id"])

        triggered.append(name)

    return triggered


def _activate_referral_sequence(
    email: str, business_name: str, days_since: int, client_record_id: str
) -> None:
    """Add the client to the Instantly.ai referral campaign."""
    api_key = os.environ["INSTANTLY_API_KEY"]

    if not REFERRAL_CAMPAIGN_ID:
        print("[referral] INSTANTLY_REFERRAL_CAMPAIGN_ID not set — skipping API call")
        return

    payload = {
        "api_key": api_key,
        "campaign_id": REFERRAL_CAMPAIGN_ID,
        "email": email,
        "first_name": business_name.split("'")[0].split(" ")[0],
        "personalization_variables": {
            "business_name": business_name,
            "days_since_onboarding": str(days_since),
        },
    }

    resp = requests.post(
        f"{INSTANTLY_API}/lead/add",
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()

    # mark as sent so we don't re-trigger
    db._get_base().table("Clients").update(
        client_record_id,
        {"referral_email_sent": True}
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    names = check_and_trigger(dry_run=args.dry_run)
    print(f"[referral] {'(dry-run) ' if args.dry_run else ''}triggered {len(names)}: {names}")
