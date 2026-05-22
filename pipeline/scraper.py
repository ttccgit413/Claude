"""
Scrapes Google Maps via Apify and extracts Instagram handles from business websites.
"""
import os
import re
import requests
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

_IG_HANDLE_RE = re.compile(
    r'instagram\.com/(?!p/|reel/|explore/)([A-Za-z0-9._]{1,30})/?',
    re.IGNORECASE,
)


def _extract_ig_handle_from_website(url: str) -> str | None:
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        matches = _IG_HANDLE_RE.findall(resp.text)
        if matches:
            # strip query params / fragments that slipped through
            handle = matches[0].split("?")[0].strip("/")
            return handle if len(handle) >= 2 else None
    except Exception:
        pass
    return None


def scrape_google_maps(query: str, location: str, max_items: int = 100) -> list[dict]:
    """
    Run Apify Google Maps scraper and return raw business records.
    Each record includes name, address, website, email, phone,
    google_rating, google_review_count, category, instagram_handle.
    """
    client = ApifyClient(os.environ["APIFY_API_TOKEN"])
    actor_id = os.environ.get("APIFY_ACTOR_ID", "compass/google-maps-scraper")

    run_input = {
        "searchStringsArray": [f"{query} {location}"],
        "maxCrawledPlacesPerSearch": max_items,
        "language": "en",
        "includeWebResults": False,
    }

    run = client.actor(actor_id).call(run_input=run_input)
    dataset = client.dataset(run["defaultDatasetId"])

    results = []
    for item in dataset.iterate_items():
        website = (item.get("website") or "").strip()
        ig_handle = (
            item.get("instagram")
            or _extract_ig_handle_from_website(website)
        )

        record = {
            "name": item.get("title", ""),
            "address": item.get("address", ""),
            "website": website,
            "email": (item.get("email") or "").strip().lower(),
            "phone": item.get("phone", ""),
            "google_rating": item.get("totalScore"),
            "google_review_count": item.get("reviewsCount", 0),
            "category": (item.get("categoryName") or "").strip(),
            "instagram_handle": ig_handle,
        }

        # skip records without an email (can't cold-email them)
        if not record["email"]:
            continue

        results.append(record)

    return results
