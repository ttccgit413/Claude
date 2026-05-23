import { notFound, redirect } from "next/navigation";
import { cookies } from "next/headers";
import {
  getClientByReportSlug,
  getLeadBySlug,
  getImageVariantsForLead,
  getMonthlySnapshots,
} from "@/lib/airtable";
import { getIgProfile, getRecentMedia } from "@/lib/instagram";
import { getGmbRating } from "@/lib/google-business";
import ReportPage from "@/components/ReportPage";

interface Props {
  params: Promise<{ slug: string }>;
}

export default async function ReportRoute({ params }: Props) {
  const { slug } = await params;

  // auth check
  const cookieStore = await cookies();
  const authCookie = cookieStore.get(`report_auth_${slug}`);
  if (!authCookie) {
    redirect(`/report/${slug}/login`);
  }

  const client = await getClientByReportSlug(slug);
  if (!client) notFound();

  const leadId = client.lead_id[0];
  const [lead, snapshots] = await Promise.all([
    getLeadBySlug(slug),
    getMonthlySnapshots(client.id),
  ]);
  if (!lead) notFound();

  // fetch live IG data (fails gracefully)
  let igProfile = null;
  let recentMedia: Awaited<ReturnType<typeof getRecentMedia>> = [];
  if (client.ig_access_token) {
    try {
      [igProfile, recentMedia] = await Promise.all([
        getIgProfile(client.ig_access_token),
        getRecentMedia(client.ig_access_token, 12),
      ]);
    } catch {
      // continue without live IG data
    }
  }

  // fetch live GMB rating (fails gracefully)
  let gmbRating = null;
  if (client.gmb_location_name && client.gmb_access_token) {
    try {
      gmbRating = await getGmbRating(client.gmb_location_name, client.gmb_access_token);
    } catch {
      // continue without live GMB data
    }
  }

  // fetch approved image variants for next-month preview section
  const variants = await getImageVariantsForLead(leadId);
  const approvedVariants = variants.filter((v) => v.verdict === "PASS").slice(0, 3);

  const competitors: { name: string; posts_per_week: number; rating: number }[] = JSON.parse(
    lead.competitors_json || "[]"
  );

  return (
    <ReportPage
      lead={lead}
      client={client}
      snapshots={snapshots}
      igProfile={igProfile}
      recentMedia={recentMedia}
      gmbRating={gmbRating}
      approvedVariants={approvedVariants}
      competitors={competitors}
    />
  );
}
