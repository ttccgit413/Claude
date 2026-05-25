"""
Main pipeline orchestrator. Run directly or triggered by the Vercel cron endpoint.

Usage:
  python run_pipeline.py --query "hair salons" --location "Melbourne" --limit 100

Steps executed:
  1. Scrape Google Maps via Apify
  2. Enrich each lead (IG stats, brand colors, competitors)
  3. Score each lead (hot/warm/cold)
  4. Write hot leads to Airtable (skip duplicates)
  5. Generate images + AI review (handled by image_gen.py and ai_reviewer.py)
  6. Telegram notification when new leads are ready for review
"""
import argparse
import json
import time

import airtable_client as db
from scraper import scrape_google_maps
from enricher import check_instagram, scrape_brand, get_competitors
from scorer import score_lead
from notify import telegram


def run(query: str, location: str, limit: int = 100) -> dict:
    print(f"[pipeline] starting — query='{query} {location}', limit={limit}")

    existing_emails = db.get_all_lead_emails()
    raw_leads = scrape_google_maps(query, location, max_items=limit)
    print(f"[pipeline] scraped {len(raw_leads)} raw leads")

    new_hot = 0
    for biz in raw_leads:
        email = biz.get("email", "").lower()

        if not email or email in existing_emails:
            continue

        # enrich
        ig = check_instagram(biz.get("instagram_handle", ""))
        time.sleep(2)  # rate limit buffer between IG calls

        brand = scrape_brand(biz.get("website", ""))

        score, tier = score_lead(biz, ig)

        suburb = _parse_suburb(biz.get("address", ""))
        competitors = get_competitors(suburb, biz.get("category", query)) if tier == "hot" else []

        # write to Airtable
        lead_data = {
            "name": biz["name"],
            "address": biz["address"],
            "website": biz.get("website", ""),
            "email": email,
            "phone": biz.get("phone", ""),
            "google_rating": biz.get("google_rating"),
            "google_review_count": biz.get("google_review_count", 0),
            "category": biz.get("category", ""),
            "instagram_handle": biz.get("instagram_handle", ""),
            "ig_followers": ig.get("ig_followers", 0),
            "ig_days_inactive": ig.get("ig_days_inactive", 0),
            "ig_avg_likes": ig.get("ig_avg_likes", 0),
            "score": score,
            "status": tier,
            "pipeline_status": "scored",
            "brand_primary_hex": brand.get("brand_primary_hex", ""),
            "brand_secondary_hex": brand.get("brand_secondary_hex", ""),
            "brand_logo_url": brand.get("brand_logo_url", ""),
            "competitors_json": json.dumps(competitors),
        }

        lead_id = db.create_lead(lead_data)
        existing_emails.add(email)
        print(f"[pipeline] saved lead {biz['name']} — score={score} tier={tier} id={lead_id}")

        if tier == "hot":
            new_hot += 1
            _run_image_pipeline(lead_id, lead_data, brand)

    if new_hot > 0:
        telegram(f"Pipeline done: {new_hot} new HOT leads ready at /review")

    return {"new_hot": new_hot, "total_scraped": len(raw_leads)}


def _run_image_pipeline(lead_id: str, lead_data: dict, brand: dict) -> None:
    from image_gen import generate_images
    from ai_reviewer import review_images_for_lead

    print(f"[pipeline] generating images for {lead_data['name']}")
    s3_urls = generate_images(lead_id, lead_data, brand)

    if not s3_urls:
        print(f"[pipeline] image gen failed for {lead_data['name']}")
        return

    db.update_lead(lead_id, {"pipeline_status": "images_generated"})

    print(f"[pipeline] AI reviewing images for {lead_data['name']}")
    passed = review_images_for_lead(lead_id, s3_urls, lead_data["name"])

    if passed:
        db.update_lead(lead_id, {"pipeline_status": "ready_for_review"})
        print(f"[pipeline] {lead_data['name']} ready for human review")
    else:
        print(f"[pipeline] {lead_data['name']} failed AI review — regenerating once")
        s3_urls_retry = generate_images(lead_id, lead_data, brand, refined=True)
        if s3_urls_retry:
            passed_retry = review_images_for_lead(lead_id, s3_urls_retry, lead_data["name"])
            if passed_retry:
                db.update_lead(lead_id, {"pipeline_status": "ready_for_review"})
                return
        db.update_lead(lead_id, {"pipeline_status": "ai_review_failed"})


def _parse_suburb(address: str) -> str:
    # "342 Smith St, Collingwood VIC 3066" → "Collingwood"
    parts = address.split(",")
    if len(parts) >= 2:
        suburb_part = parts[1].strip().split(" ")[0]
        return suburb_part
    return ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="hair salons", help="Search query")
    parser.add_argument("--location", default="Melbourne", help="Location")
    parser.add_argument("--limit", type=int, default=100, help="Max results from Apify")
    args = parser.parse_args()

    result = run(args.query, args.location, args.limit)
    print(f"[pipeline] complete — {result}")
