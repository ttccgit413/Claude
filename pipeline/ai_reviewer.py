"""
Reviews generated Instagram post images using Claude Haiku (vision).
Scores each image 1-10 across 4 criteria; avg >= 7.0 is a PASS.
Writes scores back to Airtable ImageVariants records.
"""
import json
import os

import anthropic
from dotenv import load_dotenv
import airtable_client as db

load_dotenv()

_client = None

_REVIEW_SYSTEM = """
You are a social media marketing quality reviewer. You evaluate Instagram post images for local businesses.
Always respond with valid JSON only — no preamble, no markdown fences.
"""

_REVIEW_PROMPT = """
Review this Instagram post image created for {business_name}.

Score each criterion from 1 to 10:
- professionalism: Does it look like a real, polished salon post (not AI-generated slop)?
- quality: Is it sharp, well-lit, visually appealing with no artefacts or distortions?
- text: Is the text overlay clean, readable, and professionally placed?
- overall: Would a business owner be proud to post this on their Instagram?

Return this exact JSON structure:
{{
  "scores": {{
    "professionalism": <1-10>,
    "quality": <1-10>,
    "text": <1-10>,
    "overall": <1-10>
  }},
  "avg": <float>,
  "issues": [<list of specific issues, or empty list>],
  "verdict": "PASS" or "FAIL",
  "recommendation": "<one sentence>"
}}

verdict is PASS if avg >= 7.0, otherwise FAIL.
"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def review_image(image_url: str, business_name: str) -> dict:
    """
    Sends one image to Claude Haiku for QA. Returns parsed review dict.
    """
    client = _get_client()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=_REVIEW_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": image_url,
                        },
                    },
                    {
                        "type": "text",
                        "text": _REVIEW_PROMPT.format(business_name=business_name),
                    },
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()
    result = json.loads(raw)

    # normalise avg in case model didn't compute it correctly
    scores = result["scores"]
    computed_avg = round(sum(scores.values()) / len(scores), 2)
    result["avg"] = computed_avg
    result["verdict"] = "PASS" if computed_avg >= 7.0 else "FAIL"

    return result


def review_images_for_lead(lead_id: str, s3_urls: list[str], business_name: str) -> bool:
    """
    Reviews all variants for a lead, writes scores to Airtable.
    Returns True if at least one variant PASSes (avg >= 7.0).
    """
    variants = db.get_image_variants_for_lead(lead_id)
    url_to_variant = {v["s3_url"]: v for v in variants}

    any_pass = False
    best_avg = 0.0
    best_variant_id = None

    for url in s3_urls:
        variant = url_to_variant.get(url)
        if not variant:
            continue

        try:
            result = review_image(url, business_name)
        except Exception as e:
            print(f"[ai_reviewer] review failed for {url}: {e}")
            continue

        db.update_image_variant(variant["id"], {
            "scores_json": json.dumps(result["scores"]),
            "avg_score": result["avg"],
            "verdict": result["verdict"],
        })

        if result["verdict"] == "PASS":
            any_pass = True

        if result["avg"] > best_avg:
            best_avg = result["avg"]
            best_variant_id = variant["id"]

    return any_pass
