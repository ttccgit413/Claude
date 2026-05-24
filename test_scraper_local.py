"""
Run this locally to test the Playwright scraper:
    pip install playwright requests python-dotenv
    playwright install chromium
    python test_scraper_local.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "pipeline"))

from scraper import scrape_google_maps

QUERY    = "hair salons"
LOCATION = "Melbourne"
LIMIT    = 10

print(f"\nScraping: '{QUERY}' in {LOCATION} (limit {LIMIT})\n")
print("-" * 80)

leads = scrape_google_maps(QUERY, LOCATION, max_items=LIMIT)

if not leads:
    print("No leads returned — check your internet connection or try a different query.")
    sys.exit(1)

print(f"\n{'#':<4} {'Name':<30} {'Rating':>6} {'Reviews':>8} {'IG Handle':<22} {'Email'}")
print("-" * 100)

for i, lead in enumerate(leads, 1):
    print(
        f"{i:<4} "
        f"{lead['name'][:28]:<30} "
        f"{str(lead.get('google_rating') or '-'):>6} "
        f"{lead.get('google_review_count', 0):>8} "
        f"{(lead.get('instagram_handle') or '-')[:20]:<22} "
        f"{lead.get('email', '-')}"
    )

print(f"\n{len(leads)} leads found.\n")

# Score them too
from scorer import score_lead

print(f"\n{'#':<4} {'Name':<30} {'Score':>6} {'Tier'}")
print("-" * 50)
for i, lead in enumerate(leads, 1):
    ig = {
        "ig_days_inactive": lead.get("ig_days_inactive", 0),
        "ig_followers": lead.get("ig_followers", 0),
    }
    score, tier = score_lead(lead, ig)
    print(f"{i:<4} {lead['name'][:28]:<30} {score:>6} {tier.upper()}")
