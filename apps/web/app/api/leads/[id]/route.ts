import { NextRequest, NextResponse } from "next/server";
import { updateLead } from "@/lib/airtable";

interface Props {
  params: Promise<{ id: string }>;
}

export async function PATCH(req: NextRequest, { params }: Props) {
  const { id } = await params;
  const fields = await req.json();
  await updateLead(id, fields);
  return NextResponse.json({ ok: true });
}
