"""
Step 10 — Content Package Generator.

For each onboarded client, generates a full month of:
  - 12 post captions (3/week: Tue, Thu, Sat)
  - A posting schedule PDF-ready text block
  - Two hashtag sets (reach + local)

Output is written to the Airtable ContentPackages table and returned as a dict
so the caller can upload to Google Drive or email directly.

Usage:
  python content_generator.py --client-slug bellas-hair-salon
  python content_generator.py --all
"""
import argparse
import calendar
import datetime
import os

from anthropic import Anthropic
from dotenv import load_dotenv
import airtable_client as db

load_dotenv()

_client = None

POSTING_DAYS = [1, 3, 5]  # Tue=1, Thu=3, Sat=5 (Mon=0)
POSTING_TIMES = {1: "7:00 PM", 3: "7:00 PM", 5: "10:00 AM"}

CAPTION_SYSTEM = """
You are a social media copywriter for local hair salons in Melbourne, Australia.
Write captions that are warm, aspirational and brand-consistent.
Never use em-dashes. Keep each caption under 150 words.
Always end with a call to action and "link in bio".
Return only the caption text — no numbering, no JSON, no preamble.
"""

CAPTION_THEMES = [
    ("transformation", "A dramatic hair colour transformation reveal — before/after."),
    ("behind_the_scenes", "A peek behind the scenes at the salon — a stylist at work."),
    ("product_spotlight", "Spotlight on a favourite product used in the salon."),
    ("client_love", "A glowing client reaction after their appointment."),
    ("tips", "A quick haircare tip from the team."),
    ("seasonal", "A seasonal style or trend the salon is loving right now."),
    ("team", "Introducing a team member and their signature style."),
    ("booking_push", "A direct call to book before spots fill up this week."),
    ("style_inspo", "Style inspiration — a mood board post for the season."),
    ("results", "Close-up of a stunning cut or colour result from this week."),
    ("community", "The salon's connection to the local Collingwood community."),
    ("offer", "A limited offer or package available this month."),
]


def _get_client_obj() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _generate_caption(business_name: str, category: str, theme_desc: str, suburb: str) -> str:
    response = _get_client_obj().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=CAPTION_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Write an Instagram caption for {business_name}, a {category} in {suburb}, Melbourne.\n"
                f"Theme: {theme_desc}\n"
                f"Include 3-5 relevant hashtags inline or at the end."
            ),
        }],
    )
    return response.content[0].text.strip()


def _build_posting_schedule(month: int, year: int) -> list[dict]:
    """Returns list of {date, day_name, time, slot_number} for posting days in the month."""
    slots = []
    slot_num = 1
    num_days = calendar.monthrange(year, month)[1]
    for day in range(1, num_days + 1):
        dt = datetime.date(year, month, day)
        if dt.weekday() in POSTING_DAYS and slot_num <= 12:
            slots.append({
                "date": dt.strftime("%-d %b"),
                "day_name": dt.strftime("%A"),
                "time": POSTING_TIMES[dt.weekday()],
                "slot_number": slot_num,
            })
            slot_num += 1
    return slots


def _build_hashtag_sets(business_name: str, suburb: str, category: str) -> dict:
    category_tag = category.replace(" ", "").replace("-", "")
    suburb_tag = suburb.replace(" ", "")
    return {
        "reach": (
            f"#Melbourne{category_tag} #{category_tag} #Melbourne #MelbourneStyle "
            f"#AustralianSalon #HairGoals #HairInspo #Balayage #HairColour "
            f"#MelbourneHair #SalonLife #HairTransformation"
        ),
        "local": (
            f"#{suburb_tag} #{suburb_tag}Hair #{suburb_tag}Salon "
            f"#Collingwood #Fitzroy #InnerMelbourne "
            f"#{business_name.split()[0]}Hair #LocalSalon #SupportLocal #Melbourne{suburb_tag}"
        ),
    }


def generate_content_package(client_id: str) -> dict | None:
    base = db._get_base()

    client_records = base.table("Clients").all(
        formula=f"RECORD_ID() = '{client_id}'"
    )
    if not client_records:
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

    name = lead["name"]
    category = lead.get("category", "Hair Salon")
    suburb = lead.get("address", "").split(",")[1].strip().split(" ")[0] if "," in lead.get("address", "") else "Melbourne"

    now = datetime.datetime.utcnow()
    month, year = now.month, now.year

    print(f"[content] generating {month}/{year} package for {name}")

    schedule = _build_posting_schedule(month, year)
    hashtags = _build_hashtag_sets(name, suburb, category)

    captions = []
    for i, slot in enumerate(schedule):
        theme_key, theme_desc = CAPTION_THEMES[i % len(CAPTION_THEMES)]
        print(f"[content]   caption {i + 1}/12: {theme_key}")
        text = _generate_caption(name, category, theme_desc, suburb)
        captions.append({
            "slot_number": slot["slot_number"],
            "date": slot["date"],
            "day": slot["day_name"],
            "time": slot["time"],
            "theme": theme_key,
            "caption": text,
        })

    schedule_text = _render_schedule_text(name, month, year, captions)

    package = {
        "client_id": client_id,
        "business_name": name,
        "month": f"{year}-{month:02d}",
        "captions": captions,
        "hashtag_reach": hashtags["reach"],
        "hashtag_local": hashtags["local"],
        "schedule_text": schedule_text,
    }

    _save_package(package)
    return package


def _render_schedule_text(name: str, month: int, year: int, captions: list[dict]) -> str:
    month_name = calendar.month_name[month]
    lines = [f"POSTING SCHEDULE — {name.upper()} — {month_name} {year}", ""]
    for c in captions:
        lines.append(f"Post {c['slot_number']:2d}  {c['day'][:3]} {c['date']}  {c['time']}")
        lines.append(f"       Theme: {c['theme'].replace('_', ' ').title()}")
        lines.append("")
    lines += [
        "HASHTAG SETS",
        "",
        "Set A (reach):",
        "",
        "Set B (local):",
        "",
    ]
    return "\n".join(lines)


def _save_package(package: dict) -> None:
    base = db._get_base()
    existing = base.table("ContentPackages").all(
        formula=f"AND({{client_id}} = '{package['client_id']}', {{month}} = '{package['month']}')"
    )
    import json
    fields = {
        "client_id": [package["client_id"]],
        "month": package["month"],
        "captions_json": json.dumps(package["captions"]),
        "hashtag_reach": package["hashtag_reach"],
        "hashtag_local": package["hashtag_local"],
        "schedule_text": package["schedule_text"],
    }
    if existing:
        base.table("ContentPackages").update(existing[0]["id"], fields)
    else:
        base.table("ContentPackages").create(fields)
    print(f"[content] saved package for {package['business_name']} {package['month']}")


def generate_all() -> list[dict]:
    base = db._get_base()
    clients = base.table("Clients").all(formula="NOT({report_slug} = '')")
    results = []
    for record in clients:
        pkg = generate_content_package(record["id"])
        if pkg:
            results.append(pkg)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--client-slug", help="report_slug of a single client")
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.all:
        pkgs = generate_all()
        print(f"[content] generated {len(pkgs)} packages")
    else:
        base = db._get_base()
        records = base.table("Clients").all(
            formula=f"{{report_slug}} = '{args.client_slug}'"
        )
        if not records:
            print(f"Client '{args.client_slug}' not found")
        else:
            pkg = generate_content_package(records[0]["id"])
            if pkg:
                for c in pkg["captions"]:
                    print(f"\n--- Post {c['slot_number']} ({c['day']} {c['date']}) ---")
                    print(c["caption"])
