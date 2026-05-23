import { NextRequest, NextResponse } from "next/server";

interface Props {
  params: Promise<{ id: string }>;
}

// Server-side proxy so PIPELINE_SERVICE_URL and CRON_SECRET never reach the browser.
export async function POST(_req: NextRequest, { params }: Props) {
  const { id } = await params;

  const pipelineUrl = process.env.PIPELINE_SERVICE_URL;
  if (!pipelineUrl) {
    return NextResponse.json({ error: "pipeline service not configured" }, { status: 500 });
  }

  const res = await fetch(`${pipelineUrl}/leads/${id}/regenerate`, {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.CRON_SECRET}` },
  });

  return NextResponse.json({ ok: res.ok }, { status: res.ok ? 200 : 502 });
}
