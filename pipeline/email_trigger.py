"""
Activates an Instantly.ai email sequence for a lead.
The campaign must already be configured in the Instantly.ai dashboard with
personalisation variables: {{business_name}}, {{competitor_name}},
{{days_inactive}}, {{landing_url}}, {{google_rating}}, {{area_avg_rating}}.
"""
import json
import os
import requests
from dotenv import load_dotenv
import airtable_client as db

load_dotenv()

INSTANTLY_API = "https://api.instantly.ai/api/v1"


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
