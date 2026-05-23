import { NextRequest, NextResponse } from "next/server";

// Runs on the 25th of each month — generates next month's caption packages for all clients.
export async function GET(req: NextRequest) {
  const secret = req.headers.get("authorization");
  if (secret !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const pipelineUrl = process.env.PIPELINE_SERVICE_URL;
  if (!pipelineUrl) {
    return NextResponse.json({ error: "PIPELINE_SERVICE_URL not set" }, { status: 500 });
  }

  const res = await fetch(`${pipelineUrl}/content/generate`, {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.CRON_SECRET}` },
  });

  return NextResponse.json({ ok: res.ok, status: res.status });
}
