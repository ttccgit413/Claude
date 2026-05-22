import { notFound } from "next/navigation";
import { getLeadBySlug, getImageVariantsForLead } from "@/lib/airtable";
import LandingPage from "@/components/LandingPage";

interface Props {
  params: Promise<{ slug: string }>;
}

export default async function PreviewPage({ params }: Props) {
  const { slug } = await params;
  const lead = await getLeadBySlug(slug);
  if (!lead) notFound();

  // Check 14-day expiry
  if (lead.created_at) {
    const created = new Date(lead.created_at).getTime();
    const now = Date.now();
    const FOURTEEN_DAYS_MS = 14 * 24 * 60 * 60 * 1000;
    if (now - created > FOURTEEN_DAYS_MS) {
      return (
        <main className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
          <div className="max-w-sm text-center">
            <p className="text-4xl">⏱</p>
            <h1 className="mt-4 text-xl font-semibold text-gray-800">This preview has expired</h1>
            <p className="mt-2 text-sm text-gray-500">
              This offer was valid for 14 days. If you&apos;d like to see it again, reply to
              Mike&apos;s email.
            </p>
          </div>
        </main>
      );
    }
  }

  const variants = await getImageVariantsForLead(lead.id);
  const passedVariants = variants.filter((v) => v.verdict === "PASS" || v.avg_score >= 6.5);

  return <LandingPage lead={lead} variants={passedVariants} />;
}
