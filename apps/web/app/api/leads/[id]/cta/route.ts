import { NextRequest, NextResponse } from "next/server";
import { updateLead } from "@/lib/airtable";
import { sendTelegram } from "@/lib/telegram";

interface Props {
  params: Promise<{ id: string }>;
}

export async function POST(req: NextRequest, { params }: Props) {
  const { id } = await params;
  const { name, email } = await req.json();

  if (!name || !email) {
    return NextResponse.json({ error: "missing fields" }, { status: 400 });
  }

  await updateLead(id, { pipeline_status: "cta_clicked" } as Parameters<typeof updateLead>[1]);

  await sendTelegram(
    `🔥 CTA CLICK — lead page\nName: ${name}\nEmail: ${email}\nLead ID: ${id}`
  );

  return NextResponse.json({ ok: true });
}
