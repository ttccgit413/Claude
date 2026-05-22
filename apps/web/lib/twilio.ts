import twilio from "twilio";

export function sendSms(message: string): Promise<void> {
  const client = twilio(
    process.env.TWILIO_ACCOUNT_SID!,
    process.env.TWILIO_AUTH_TOKEN!
  );
  return client.messages
    .create({
      body: message,
      from: process.env.TWILIO_FROM_NUMBER!,
      to: process.env.TWILIO_TO_NUMBER!,
    })
    .then(() => undefined);
}
