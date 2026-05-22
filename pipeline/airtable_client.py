import os
from typing import Optional
from pyairtable import Api
from dotenv import load_dotenv

load_dotenv()

_api = None
_base = None


def _get_base():
    global _api, _base
    if _base is None:
        _api = Api(os.environ["AIRTABLE_API_KEY"])
        _base = _api.base(os.environ["AIRTABLE_BASE_ID"])
    return _base


# ── Leads ──────────────────────────────────────────────────────────────────


def get_all_lead_emails() -> set[str]:
    table = _get_base().table("Leads")
    records = table.all(fields=["email"])
    return {r["fields"]["email"] for r in records if "email" in r["fields"]}


def create_lead(data: dict) -> str:
    table = _get_base().table("Leads")
    record = table.create(data)
    return record["id"]


def update_lead(record_id: str, fields: dict) -> None:
    table = _get_base().table("Leads")
    table.update(record_id, fields)


def get_leads_by_status(pipeline_status: str) -> list[dict]:
    table = _get_base().table("Leads")
    records = table.all(
        formula=f"{{pipeline_status}} = '{pipeline_status}'"
    )
    return [{"id": r["id"], **r["fields"]} for r in records]


def get_lead_by_slug(slug: str) -> Optional[dict]:
    table = _get_base().table("Leads")
    records = table.all(formula=f"{{landing_page_slug}} = '{slug}'")
    if not records:
        return None
    r = records[0]
    return {"id": r["id"], **r["fields"]}


def get_lead_by_email(email: str) -> Optional[dict]:
    table = _get_base().table("Leads")
    records = table.all(formula=f"{{email}} = '{email}'")
    if not records:
        return None
    r = records[0]
    return {"id": r["id"], **r["fields"]}


# ── ImageVariants ──────────────────────────────────────────────────────────


def create_image_variant(lead_id: str, variant_number: int, s3_url: str) -> str:
    table = _get_base().table("ImageVariants")
    record = table.create({
        "lead_id": [lead_id],
        "variant_number": variant_number,
        "s3_url": s3_url,
    })
    return record["id"]


def update_image_variant(record_id: str, fields: dict) -> None:
    table = _get_base().table("ImageVariants")
    table.update(record_id, fields)


def get_image_variants_for_lead(lead_id: str) -> list[dict]:
    table = _get_base().table("ImageVariants")
    records = table.all(formula=f"{{lead_id}} = '{lead_id}'")
    return [{"id": r["id"], **r["fields"]} for r in records]


# ── Clients ────────────────────────────────────────────────────────────────


def create_client(lead_id: str, monthly_fee: float, report_slug: str, report_password: str) -> str:
    table = _get_base().table("Clients")
    record = table.create({
        "lead_id": [lead_id],
        "monthly_fee": monthly_fee,
        "report_slug": report_slug,
        "report_password": report_password,
    })
    return record["id"]


def get_client_by_report_slug(slug: str) -> Optional[dict]:
    table = _get_base().table("Clients")
    records = table.all(formula=f"{{report_slug}} = '{slug}'")
    if not records:
        return None
    r = records[0]
    return {"id": r["id"], **r["fields"]}
