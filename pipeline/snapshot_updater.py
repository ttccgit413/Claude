"""
Pulls live Instagram and Google My Business data for all active clients
and stores a MonthlySnapshot record in Airtable.

Called monthly by POST /snapshots/update on the Railway service.
"""
import datetime
import os
import requests
from dotenv import load_dotenv
import airtable_client as db

load_dotenv()

IG_BASE = "https://graph.instagram.com"
GMB_BASE = "https://mybusinessbusinessinformation.googleapis.com/v1"


def _current_month() -> str:
    d = datetime.datetime.utcnow()
    return f"{d.year}-{d.month:02d}"


def _get_ig_data(access_token: str) -> dict:
    resp = requests.get(
        f"{IG_BASE}/me",
        params={"fields": "followers_count,media_count", "access_token": access_token},
        timeout=10,
    )
    resp.raise_for_status()
    profile = resp.json()

    media_resp = requests.get(
        f"{IG_BASE}/me/media",
        params={
            "fields": "like_count,comments_count,media_url,timestamp",
            "limit": 12,
            "access_token": access_token,
        },
        timeout=10,
    )
    media_resp.raise_for_status()
    media_items = media_resp.json().get("data", [])

    top_post = max(media_items, key=lambda m: m.get("like_count", 0)) if media_items else {}

    return {
        "followers": profile.get("followers_count", 0),
        "top_post_url": top_post.get("media_url", ""),
        "top_post_likes": top_post.get("like_count", 0),
        "top_post_comments": top_post.get("comments_count", 0),
    }


def _get_gmb_rating(location_name: str, access_token: str) -> float:
    resp = requests.get(
        f"{GMB_BASE}/{location_name}",
        params={"readMask": "rating"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("rating", 0)


def _count_posts_delivered(client_id: str) -> int:
    month = _current_month()
    base = db._get_base()
    records = base.table("PostsDelivered").all(
        formula=f"AND({{client_id}} = '{client_id}', {{month}} = '{month}')"
    )
    return len(records)


def update_all_snapshots() -> None:
    base = db._get_base()
    clients = base.table("Clients").all(formula="NOT({report_slug} = '')")

    month = _current_month()
    print(f"[snapshot] updating {len(clients)} clients for {month}")

    for record in clients:
        f = record["fields"]
        client_id = record["id"]
        client_name = f.get("report_slug", client_id)

        snapshot: dict = {"posts_delivered": _count_posts_delivered(client_id)}

        ig_token = f.get("ig_access_token")
        if ig_token:
            try:
                ig_data = _get_ig_data(ig_token)
                snapshot.update(ig_data)
            except Exception as e:
                print(f"[snapshot] IG fetch failed for {client_name}: {e}")

        gmb_location = f.get("gmb_location_name")
        gmb_token = f.get("gmb_access_token")
        if gmb_location and gmb_token:
            try:
                snapshot["google_rating"] = _get_gmb_rating(gmb_location, gmb_token)
            except Exception as e:
                print(f"[snapshot] GMB fetch failed for {client_name}: {e}")

        db.upsert_monthly_snapshot(client_id, month, snapshot)
        print(f"[snapshot] updated {client_name}: {snapshot}")
