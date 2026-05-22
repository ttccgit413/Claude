"""
FastAPI service hosted on Railway.
Exposes HTTP endpoints so the Vercel cron can trigger the Python pipeline.

Deploy: railway up (with railway.json in repo root)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Salon Lead Gen Pipeline")

CRON_SECRET = os.environ.get("CRON_SECRET", "")


def _auth(authorization: str | None):
    if authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(status_code=401, detail="unauthorized")


class RunInput(BaseModel):
    query: str = "hair salons"
    location: str = "Melbourne"
    limit: int = 100


class EmailTriggerInput(BaseModel):
    lead_id: str
    landing_url: str


@app.post("/run")
async def run_pipeline(
    body: RunInput,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
):
    _auth(authorization)
    background_tasks.add_task(_do_run, body.query, body.location, body.limit)
    return {"ok": True, "message": "pipeline started in background"}


@app.post("/email/trigger")
async def trigger_email(
    body: EmailTriggerInput,
    authorization: str | None = Header(default=None),
):
    _auth(authorization)
    import airtable_client as db
    from email_trigger import activate_sequence

    lead = db.get_lead_by_slug(body.lead_id)
    if not lead:
        # try by record id via direct Airtable lookup
        raise HTTPException(status_code=404, detail="lead not found")

    activate_sequence(lead, body.landing_url)
    return {"ok": True}


@app.post("/leads/{lead_id}/regenerate")
async def regenerate_images(
    lead_id: str,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
):
    _auth(authorization)
    background_tasks.add_task(_do_regenerate, lead_id)
    return {"ok": True, "message": "regeneration started"}


def _do_run(query: str, location: str, limit: int):
    from run_pipeline import run
    run(query, location, limit)


def _do_regenerate(lead_id: str):
    import airtable_client as db
    from image_gen import generate_images
    from ai_reviewer import review_images_for_lead

    lead = None
    # fetch lead data from Airtable
    records = db._get_base().table("Leads").all(
        formula=f"RECORD_ID() = '{lead_id}'"
    )
    if not records:
        return
    r = records[0]
    lead = {"id": r["id"], **r["fields"]}

    brand = {
        "brand_primary_hex": lead.get("brand_primary_hex", ""),
        "brand_secondary_hex": lead.get("brand_secondary_hex", ""),
    }
    s3_urls = generate_images(lead_id, lead, brand, refined=True)
    if s3_urls:
        passed = review_images_for_lead(lead_id, s3_urls, lead["name"])
        if passed:
            db.update_lead(lead_id, {"pipeline_status": "ready_for_review"})
