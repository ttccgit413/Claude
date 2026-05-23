import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

interface Props {
  params: Promise<{ id: string }>;
}

// Server-side proxy so PIPELINE_SERVICE_URL and CRON_SECRET never reach the browser.
export async function POST(_req: NextRequest, { params }: Props) {
  const cookieStore = await cookies();
  if (cookieStore.get("review_auth")?.value !== "1") {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

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
