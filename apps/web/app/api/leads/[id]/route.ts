import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { updateLead } from "@/lib/airtable";

interface Props {
  params: Promise<{ id: string }>;
}

export async function PATCH(req: NextRequest, { params }: Props) {
  const cookieStore = await cookies();
  if (cookieStore.get("review_auth")?.value !== "1") {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const { id } = await params;
  const fields = await req.json();
  await updateLead(id, fields);
  return NextResponse.json({ ok: true });
}
