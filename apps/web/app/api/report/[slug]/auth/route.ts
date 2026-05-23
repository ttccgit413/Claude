import { NextRequest, NextResponse } from "next/server";
import { getClientByReportSlug } from "@/lib/airtable";

interface Props {
  params: Promise<{ slug: string }>;
}

export async function POST(req: NextRequest, { params }: Props) {
  const { slug } = await params;
  const { password } = await req.json();

  const client = await getClientByReportSlug(slug);
  if (!client) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }

  if (password !== client.report_password) {
    return NextResponse.json({ error: "wrong password" }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(`report_auth_${slug}`, "1", {
    httpOnly: true,
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30, // 30 days
    path: `/report/${slug}`,
  });
  return response;
}
