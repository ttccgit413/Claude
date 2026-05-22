"""
Generates 3 branded Instagram post image variants for a lead using GPT image-1,
uploads each to S3, and writes ImageVariant records to Airtable.
"""
import base64
import io
import os
import uuid

import boto3
from openai import OpenAI
from dotenv import load_dotenv
import airtable_client as db

load_dotenv()

_openai = None
_s3 = None


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _openai


def _get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client(
            "s3",
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            region_name=os.environ.get("AWS_REGION", "ap-southeast-2"),
        )
    return _s3


_VARIANT_STYLES = [
    "a stunning balayage colour result on a client, shot from behind, golden hour lighting",
    "a close-up of a freshly styled blowout, editorial fashion photography, clean white background",
    "before-and-after split showing hair colour transformation, dramatic lighting, professional studio",
]

_PROMPT_TEMPLATE = """
Create a professional Instagram post image for {business_name}, a {category} in Melbourne, Australia.

Brand colours: primary {primary_hex}, secondary {secondary_hex}.
Style: aspirational, warm lighting, luxury feel. Editorial photography aesthetic.
Scene: {scene_description}.
Text overlay: "{business_name}" in elegant serif font at the bottom third, using the primary brand colour.
Format: square 1080x1080 composition. No stock photo feel. Real salon energy. No watermarks.
"""


def _upload_to_s3(image_bytes: bytes, slug: str, variant: int) -> str:
    s3 = _get_s3()
    bucket = os.environ["AWS_S3_BUCKET"]
    key = f"leads/{slug}/v{variant}-{uuid.uuid4().hex[:8]}.jpg"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=image_bytes,
        ContentType="image/jpeg",
        ACL="public-read",
    )
    region = os.environ.get("AWS_REGION", "ap-southeast-2")
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _slugify(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def generate_images(
    lead_id: str,
    lead_data: dict,
    brand: dict,
    refined: bool = False,
) -> list[str]:
    """
    Generate 3 image variants. Returns list of S3 URLs (empty on failure).
    If refined=True, adds extra prompt guidance to address common AI-slop issues.
    """
    client = _get_openai()
    slug = _slugify(lead_data.get("name", lead_id))

    primary = brand.get("brand_primary_hex") or lead_data.get("brand_primary_hex") or "#C4A882"
    secondary = brand.get("brand_secondary_hex") or lead_data.get("brand_secondary_hex") or "#2C2C2C"

    refinement = "\nIMPORTANT: Avoid AI artefacts. Ensure sharp focus, realistic textures, natural skin tones. No distorted hands or faces." if refined else ""

    s3_urls = []
    for i, scene in enumerate(_VARIANT_STYLES, start=1):
        prompt = _PROMPT_TEMPLATE.format(
            business_name=lead_data.get("name", ""),
            category=lead_data.get("category", "Hair Salon"),
            primary_hex=primary,
            secondary_hex=secondary,
            scene_description=scene,
        ) + refinement

        try:
            response = client.images.generate(
                model="gpt-image-1",
                prompt=prompt.strip(),
                size="1024x1024",
                n=1,
            )
            image_b64 = response.data[0].b64_json
            image_bytes = base64.b64decode(image_b64)

            url = _upload_to_s3(image_bytes, slug, i)
            s3_urls.append(url)

            # write to Airtable immediately so partial results are saved
            db.create_image_variant(lead_id, i, url)

        except Exception as e:
            print(f"[image_gen] variant {i} failed: {e}")

    return s3_urls
