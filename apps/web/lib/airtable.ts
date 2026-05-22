import Airtable from "airtable";

const base = new Airtable({ apiKey: process.env.AIRTABLE_API_KEY! }).base(
  process.env.AIRTABLE_BASE_ID!
);

export interface Lead {
  id: string;
  name: string;
  address: string;
  website: string;
  email: string;
  phone: string;
  google_rating: number;
  google_review_count: number;
  category: string;
  instagram_handle: string;
  ig_followers: number;
  ig_days_inactive: number;
  ig_avg_likes: number;
  score: number;
  status: "hot" | "warm" | "cold";
  pipeline_status: string;
  approved_image_url: string;
  landing_page_slug: string;
  brand_primary_hex: string;
  brand_secondary_hex: string;
  brand_logo_url: string;
  competitors_json: string;
  created_at: string;
  reply_received: boolean;
}

export interface ImageVariant {
  id: string;
  lead_id: string[];
  variant_number: number;
  s3_url: string;
  scores_json: string;
  avg_score: number;
  verdict: "PASS" | "FAIL";
  approved: boolean;
}

function mapLead(record: Airtable.Record<Airtable.FieldSet>): Lead {
  const f = record.fields as Record<string, unknown>;
  return {
    id: record.id,
    name: (f.name as string) ?? "",
    address: (f.address as string) ?? "",
    website: (f.website as string) ?? "",
    email: (f.email as string) ?? "",
    phone: (f.phone as string) ?? "",
    google_rating: (f.google_rating as number) ?? 0,
    google_review_count: (f.google_review_count as number) ?? 0,
    category: (f.category as string) ?? "",
    instagram_handle: (f.instagram_handle as string) ?? "",
    ig_followers: (f.ig_followers as number) ?? 0,
    ig_days_inactive: (f.ig_days_inactive as number) ?? 0,
    ig_avg_likes: (f.ig_avg_likes as number) ?? 0,
    score: (f.score as number) ?? 0,
    status: (f.status as Lead["status"]) ?? "cold",
    pipeline_status: (f.pipeline_status as string) ?? "",
    approved_image_url: (f.approved_image_url as string) ?? "",
    landing_page_slug: (f.landing_page_slug as string) ?? "",
    brand_primary_hex: (f.brand_primary_hex as string) ?? "#000000",
    brand_secondary_hex: (f.brand_secondary_hex as string) ?? "#ffffff",
    brand_logo_url: (f.brand_logo_url as string) ?? "",
    competitors_json: (f.competitors_json as string) ?? "[]",
    created_at: (f.created_at as string) ?? "",
    reply_received: (f.reply_received as boolean) ?? false,
  };
}

export async function getLeadBySlug(slug: string): Promise<Lead | null> {
  const records = await base("Leads")
    .select({ filterByFormula: `{landing_page_slug} = '${slug}'` })
    .firstPage();
  if (!records.length) return null;
  return mapLead(records[0]);
}

export async function getLeadsForReview(): Promise<Lead[]> {
  const records = await base("Leads")
    .select({ filterByFormula: `{pipeline_status} = 'ready_for_review'` })
    .all();
  return records.map(mapLead);
}

export async function updateLead(id: string, fields: Partial<Lead>): Promise<void> {
  await base("Leads").update(id, fields as Airtable.FieldSet);
}

export async function getImageVariantsForLead(leadId: string): Promise<ImageVariant[]> {
  const records = await base("ImageVariants")
    .select({ filterByFormula: `{lead_id} = '${leadId}'` })
    .all();
  return records.map((r) => {
    const f = r.fields as Record<string, unknown>;
    return {
      id: r.id,
      lead_id: (f.lead_id as string[]) ?? [],
      variant_number: (f.variant_number as number) ?? 0,
      s3_url: (f.s3_url as string) ?? "",
      scores_json: (f.scores_json as string) ?? "{}",
      avg_score: (f.avg_score as number) ?? 0,
      verdict: (f.verdict as "PASS" | "FAIL") ?? "FAIL",
      approved: (f.approved as boolean) ?? false,
    };
  });
}

export async function getLeadByEmail(email: string): Promise<Lead | null> {
  const records = await base("Leads")
    .select({ filterByFormula: `{email} = '${email}'` })
    .firstPage();
  if (!records.length) return null;
  return mapLead(records[0]);
}
