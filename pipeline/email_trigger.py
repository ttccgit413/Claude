"""
Activates an Instantly.ai email sequence for a lead.
The campaign must already be configured in the Instantly.ai dashboard with
personalisation variables: {{business_name}}, {{competitor_name}},
{{days_inactive}}, {{landing_url}}, {{google_rating}}, {{area_avg_rating}},
{{case_study_blurb}} (empty string when no case study exists yet).
"""
import json
import os
import requests
from dotenv import load_dotenv
import airtable_client as db

load_dotenv()

INSTANTLY_API = "https://api.instantly.ai/api/v1"


def _get_case_study_blurb(suburb: str) -> str:
    """
    Returns a one-liner for the Day 1 email if a published case study exists.
    Falls back to empty string so the email template handles it gracefully.
    """
    try:
        base = db._get_base()
        records = base.table("CaseStudies").all(
            formula="NOT({case_study_text} = '')",
            sort=[{"field": "months_tracked", "direction": "desc"}],
            max_records=1,
        )
        if not records:
            return ""
        cs = records[0]["fields"]
        before = int(cs.get("before_followers", 0))
        after = int(cs.get("after_followers", 0))
        cs_suburb = cs.get("suburb", suburb)
        return (
            f"Helped a {cs_suburb} salon grow from {before:,} → {after:,} followers "
            f"in 30 days. Built the same thing for you:"
        )
    except Exception:
        return ""


def activate_sequence(lead: dict, landing_url: str) -> bool:
    """
    Adds the lead as a contact in the configured Instantly.ai campaign
    and marks the lead as email_sent in Airtable.
    Returns True on success.
    """
    api_key = os.environ["INSTANTLY_API_KEY"]
    campaign_id = os.environ["INSTANTLY_CAMPAIGN_ID"]

    competitors = json.loads(lead.get("competitors_json") or "[]")
    top_competitor = competitors[0]["name"] if competitors else "your top competitor"
    area_avg_rating = (
        round(sum(c["rating"] for c in competitors) / len(competitors), 1)
        if competitors else 4.4
    )
    suburb = lead.get("address", "").split(",")[1].strip().split(" ")[0] if "," in lead.get("address", "") else "Melbourne"

    payload = {
        "api_key": api_key,
        "campaign_id": campaign_id,
        "email": lead["email"],
        "first_name": _first_name(lead["name"]),
        "personalization_variables": {
            "business_name": lead["name"],
            "competitor_name": top_competitor,
            "days_inactive": str(lead.get("ig_days_inactive", 0)),
            "landing_url": landing_url,
            "google_rating": str(lead.get("google_rating") or ""),
            "area_avg_rating": str(area_avg_rating),
            "case_study_blurb": _get_case_study_blurb(suburb),
        },
    }

    resp = requests.post(
        f"{INSTANTLY_API}/lead/add",
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()

    db.update_lead(lead["id"], {"pipeline_status": "email_sent"})
    return True


def _first_name(business_name: str) -> str:
    # "Bella's Hair Salon" → "Bella" — used as fallback personalisation
    return business_name.split("'")[0].split(" ")[0]
