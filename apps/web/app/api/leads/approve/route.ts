import { NextRequest, NextResponse } from "next/server";
import { updateLead } from "@/lib/airtable";
import slugify from "slugify";

export async function POST(req: NextRequest) {
  const { leadId, approvedImageUrl, businessName } = await req.json();

  if (!leadId || !approvedImageUrl || !businessName) {
    return NextResponse.json({ error: "missing fields" }, { status: 400 });
  }

  const slug = slugify(businessName, { lower: true, strict: true });
  const landingUrl = `${process.env.NEXT_PUBLIC_APP_URL}/preview/${slug}`;

  await updateLead(leadId, {
    approved_image_url: approvedImageUrl,
    landing_page_slug: slug,
    pipeline_status: "approved",
  } as Parameters<typeof updateLead>[1]);

  // trigger Instantly.ai email sequence via the Python pipeline service
  const pipelineUrl = process.env.PIPELINE_SERVICE_URL;
  if (pipelineUrl) {
    await fetch(`${pipelineUrl}/email/trigger`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.CRON_SECRET}`,
      },
      body: JSON.stringify({ lead_id: leadId, landing_url: landingUrl }),
    }).catch((err) => {
      console.error("email trigger failed:", err);
    });
  }

  return NextResponse.json({ ok: true, slug, landingUrl });
}
