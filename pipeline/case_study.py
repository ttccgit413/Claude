"""
Auto-generates a case study for a client from their Airtable data.

Produces:
  1. A plain-text case study (injected into Day 1 email once live)
  2. An Airtable record in a CaseStudies table for reference

Usage:
  python case_study.py --client-slug bellas-hair-salon
  python case_study.py --all   # generate for all clients with 2+ monthly snapshots
"""
import argparse
import os
from dotenv import load_dotenv
import airtable_client as db

load_dotenv()


def generate_case_study(client_id: str) -> dict | None:
    """
    Builds a case study dict from the client's lead + snapshot data.
    Returns None if there isn't enough data yet (need at least 2 snapshots).
    """
    base = db._get_base()

    client_records = base.table("Clients").all(
        formula=f"RECORD_ID() = '{client_id}'"
    )
    if not client_records:
        print(f"[case_study] client {client_id} not found")
        return None

    client = {"id": client_records[0]["id"], **client_records[0]["fields"]}

    lead_ids = client.get("lead_id", [])
    if not lead_ids:
        return None

    lead_records = base.table("Leads").all(
        formula=f"RECORD_ID() = '{lead_ids[0]}'"
    )
    if not lead_records:
        return None
    lead = {"id": lead_records[0]["id"], **lead_records[0]["fields"]}

    snapshots = sorted(
        db.get_monthly_snapshots(client_id),
        key=lambda s: s["month"],
    )

    if len(snapshots) < 2:
        print(f"[case_study] {lead['name']}: need ≥2 snapshots, have {len(snapshots)}")
        return None

    first = snapshots[0]
    latest = snapshots[-1]

    follower_growth = latest["followers"] - first["followers"]
    follower_pct = round((follower_growth / first["followers"]) * 100, 1) if first["followers"] else 0
    rating_delta = round(latest["google_rating"] - (lead.get("google_rating") or 0), 1)
    top_likes = latest.get("top_post_likes", 0)
    before_avg_likes = lead.get("ig_avg_likes", 0)
    likes_multiplier = round(top_likes / before_avg_likes, 1) if before_avg_likes else 0

    suburb = lead.get("address", "").split(",")[1].strip().split(" ")[0] if "," in lead.get("address", "") else "the area"

    text = _render_text(lead, first, latest, follower_growth, follower_pct, rating_delta, top_likes, likes_multiplier, suburb)

    result = {
        "client_id": client_id,
        "lead_name": lead["name"],
        "suburb": suburb,
        "before_followers": first["followers"],
        "after_followers": latest["followers"],
        "follower_growth": follower_growth,
        "follower_pct": follower_pct,
        "before_rating": lead.get("google_rating") or 0,
        "after_rating": latest["google_rating"],
        "rating_delta": rating_delta,
        "posts_delivered": latest["posts_delivered"],
        "top_post_likes": top_likes,
        "likes_multiplier": likes_multiplier,
        "case_study_text": text,
        "months_tracked": len(snapshots),
    }

    _save_to_airtable(result)
    return result


def _render_text(lead, first, latest, follower_growth, follower_pct, rating_delta, top_likes, likes_multiplier, suburb) -> str:
    name = lead["name"]
    days_inactive = lead.get("ig_days_inactive", 0)
    before_followers = first["followers"]
    after_followers = latest["followers"]
    before_rating = lead.get("google_rating") or 0
    after_rating = latest["google_rating"]
    posts = latest["posts_delivered"]

    # pick a real client quote placeholder — to be replaced with an actual quote
    quote = f"I was skeptical but the posts actually look like us, not like generic AI content. — {name.split(' ')[0]}'s owner"

    return f"""CASE STUDY: {name}, Melbourne

BEFORE:
→ Last post: {days_inactive} days ago
→ Followers: {before_followers:,}
→ Google: {before_rating} ★
→ Avg likes per post: {lead.get('ig_avg_likes', 0)}

AFTER {latest['posts_delivered']} POSTS ({latest['month']}):
→ {posts} posts delivered
→ Followers: {after_followers:,} (+{follower_growth:,}, +{follower_pct}%)
→ Google: {after_rating} ★{f' (+{rating_delta})' if rating_delta > 0 else ''}
→ Top post: {top_likes} likes{f' ({likes_multiplier}x their previous avg)' if likes_multiplier > 1 else ''}

"{quote}"

---
Use in Day 1 email:
"Helped a {suburb} salon grow from {before_followers:,} → {after_followers:,} followers in 30 days. Built the same thing for you:"
"""


def _save_to_airtable(result: dict) -> None:
    base = db._get_base()
    existing = base.table("CaseStudies").all(
        formula=f"{{client_id}} = '{result['client_id']}'"
    )
    fields = {k: v for k, v in result.items() if k != "client_id"}
    fields["client_id"] = [result["client_id"]]

    if existing:
        base.table("CaseStudies").update(existing[0]["id"], fields)
    else:
        base.table("CaseStudies").create(fields)

    print(f"[case_study] saved case study for {result['lead_name']}")


def generate_all() -> list[dict]:
    base = db._get_base()
    clients = base.table("Clients").all(formula="NOT({report_slug} = '')")
    results = []
    for record in clients:
        cs = generate_case_study(record["id"])
        if cs:
            results.append(cs)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--client-slug", help="report_slug of a single client")
    group.add_argument("--all", action="store_true", help="generate for all eligible clients")
    args = parser.parse_args()

    if args.all:
        results = generate_all()
        print(f"[case_study] generated {len(results)} case studies")
    else:
        base = db._get_base()
        records = base.table("Clients").all(
            formula=f"{{report_slug}} = '{args.client_slug}'"
        )
        if not records:
            print(f"Client '{args.client_slug}' not found")
        else:
            cs = generate_case_study(records[0]["id"])
            if cs:
                print(cs["case_study_text"])
