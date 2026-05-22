import { getLeadsForReview, getImageVariantsForLead, type Lead, type ImageVariant } from "@/lib/airtable";
import ReviewDashboard from "@/components/ReviewDashboard";
import { redirect } from "next/navigation";
import { headers } from "next/headers";

// Simple password gate via a cookie set by a login form (not shown here).
// For production, replace with NextAuth or similar.
async function isAuthenticated(): Promise<boolean> {
  const hdrs = await headers();
  const cookie = hdrs.get("cookie") ?? "";
  return cookie.includes("review_auth=1");
}

interface LeadWithVariants {
  lead: Lead;
  variants: ImageVariant[];
}

export default async function ReviewPage() {
  if (!(await isAuthenticated())) {
    redirect("/review/login");
  }

  const leads = await getLeadsForReview();

  const leadsWithVariants: LeadWithVariants[] = await Promise.all(
    leads.map(async (lead) => ({
      lead,
      variants: await getImageVariantsForLead(lead.id),
    }))
  );

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-2 text-2xl font-bold text-gray-900">Lead Review Queue</h1>
        <p className="mb-8 text-sm text-gray-500">
          {leads.length} lead{leads.length !== 1 ? "s" : ""} waiting for approval
        </p>

        {leads.length === 0 ? (
          <div className="rounded-xl border bg-white p-12 text-center text-gray-400">
            No leads ready for review yet. Check back after the next pipeline run.
          </div>
        ) : (
          <div className="space-y-8">
            {leadsWithVariants.map(({ lead, variants }) => (
              <ReviewDashboard key={lead.id} lead={lead} variants={variants} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
