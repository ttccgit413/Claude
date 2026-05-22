import { NextRequest, NextResponse } from "next/server";
import { getLeadByEmail, updateLead } from "@/lib/airtable";
import { sendSms } from "@/lib/twilio";

// SendGrid inbound parse webhook.
// Configure at: https://app.sendgrid.com/settings/parse
// Incoming email to reply.youragency.com.au → POST here.
export async function POST(req: NextRequest) {
  const formData = await req.formData();

  const from = (formData.get("from") as string) ?? "";
  const subject = (formData.get("subject") as string) ?? "";
  const text = (formData.get("text") as string) ?? "";

  // extract plain email address from "Name <email@domain.com>"
  const emailMatch = from.match(/<(.+?)>/) ?? from.match(/\S+@\S+/);
  const senderEmail = emailMatch ? (emailMatch[1] ?? emailMatch[0]) : from;

  if (!senderEmail) {
    return NextResponse.json({ ok: true }); // ignore unparseable
  }

  const lead = await getLeadByEmail(senderEmail.toLowerCase());
  if (!lead) {
    return NextResponse.json({ ok: true }); // not a tracked lead
  }

  await updateLead(lead.id, {
    reply_received: true,
    pipeline_status: "replied",
  } as Parameters<typeof updateLead>[1]);

  const snippet = text.slice(0, 120).replace(/\n/g, " ");
  const airtableLink = `https://airtable.com/${process.env.AIRTABLE_BASE_ID}`;

  await sendSms(
    `🔥 REPLY — ${lead.name}\n${senderEmail}\nSubject: ${subject}\n"${snippet}"\nLink: ${airtableLink}`
  );

  return NextResponse.json({ ok: true });
}
