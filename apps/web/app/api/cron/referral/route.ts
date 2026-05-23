import { NextRequest, NextResponse } from "next/server";

// Runs daily — checks if any client is at ~day 28 post-onboarding and fires referral email.
export async function GET(req: NextRequest) {
  const secret = req.headers.get("authorization");
  if (secret !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const pipelineUrl = process.env.PIPELINE_SERVICE_URL;
  if (!pipelineUrl) {
    return NextResponse.json({ error: "PIPELINE_SERVICE_URL not set" }, { status: 500 });
  }

  const res = await fetch(`${pipelineUrl}/referral/trigger`, {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.CRON_SECRET}` },
  });

  return NextResponse.json({ ok: res.ok, status: res.status });
}
