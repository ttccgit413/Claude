import { NextRequest, NextResponse } from "next/server";

// Called daily at 06:00 AEST (20:00 UTC) by Vercel cron.
// Triggers the Python pipeline hosted on Railway.
export async function GET(req: NextRequest) {
  const secret = req.headers.get("authorization");
  if (secret !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const pipelineUrl = process.env.PIPELINE_SERVICE_URL;
  if (!pipelineUrl) {
    return NextResponse.json({ error: "PIPELINE_SERVICE_URL not set" }, { status: 500 });
  }

  try {
    const res = await fetch(`${pipelineUrl}/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.CRON_SECRET}`,
      },
      body: JSON.stringify({
        query: "hair salons",
        location: "Melbourne",
        limit: 100,
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json({ error: text }, { status: 502 });
    }

    const data = await res.json();
    return NextResponse.json({ ok: true, ...data });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
