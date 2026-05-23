import Airtable from "airtable";

let _base: ReturnType<Airtable["base"]> | null = null;

function base(table: string) {
  if (!_base) {
    _base = new Airtable({ apiKey: process.env.AIRTABLE_API_KEY! }).base(
      process.env.AIRTABLE_BASE_ID!
    );
  }
  return _base(table);
}

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

// ── Clients ───────────────────────────────────────────────────────────────

export interface Client {
  id: string;
  lead_id: string[];
  monthly_fee: number;
  report_slug: string;
  report_password: string;
  ig_access_token: string;
  gmb_location_name: string;
  gmb_access_token: string;
  onboarded_at: string;
}

function mapClient(record: Airtable.Record<Airtable.FieldSet>): Client {
  const f = record.fields as Record<string, unknown>;
  return {
    id: record.id,
    lead_id: (f.lead_id as string[]) ?? [],
    monthly_fee: (f.monthly_fee as number) ?? 0,
    report_slug: (f.report_slug as string) ?? "",
    report_password: (f.report_password as string) ?? "",
    ig_access_token: (f.ig_access_token as string) ?? "",
    gmb_location_name: (f.gmb_location_name as string) ?? "",
    gmb_access_token: (f.gmb_access_token as string) ?? "",
    onboarded_at: (f.onboarded_at as string) ?? "",
  };
}

export async function getClientByReportSlug(slug: string): Promise<Client | null> {
  const records = await base("Clients")
    .select({ filterByFormula: `{report_slug} = '${slug}'` })
    .firstPage();
  if (!records.length) return null;
  return mapClient(records[0]);
}

export async function updateClient(id: string, fields: Partial<Client>): Promise<void> {
  await base("Clients").update(id, fields as Airtable.FieldSet);
}

// ── MonthlyStats ──────────────────────────────────────────────────────────
// Snapshot stored monthly so we can show growth over time.

export interface MonthlySnapshot {
  id: string;
  client_id: string[];
  month: string;        // "2025-06"
  followers: number;
  google_rating: number;
  posts_delivered: number;
  top_post_url: string;
  top_post_likes: number;
  top_post_comments: number;
  top_post_reach: number;
}

export async function getMonthlySnapshots(clientId: string): Promise<MonthlySnapshot[]> {
  const records = await base("MonthlySnapshots")
    .select({
      filterByFormula: `{client_id} = '${clientId}'`,
      sort: [{ field: "month", direction: "asc" }],
    })
    .all();
  return records.map((r) => {
    const f = r.fields as Record<string, unknown>;
    return {
      id: r.id,
      client_id: (f.client_id as string[]) ?? [],
      month: (f.month as string) ?? "",
      followers: (f.followers as number) ?? 0,
      google_rating: (f.google_rating as number) ?? 0,
      posts_delivered: (f.posts_delivered as number) ?? 0,
      top_post_url: (f.top_post_url as string) ?? "",
      top_post_likes: (f.top_post_likes as number) ?? 0,
      top_post_comments: (f.top_post_comments as number) ?? 0,
      top_post_reach: (f.top_post_reach as number) ?? 0,
    };
  });
}

export async function upsertMonthlySnapshot(
  clientId: string,
  month: string,
  data: Partial<Omit<MonthlySnapshot, "id" | "client_id" | "month">>
): Promise<void> {
  const existing = await base("MonthlySnapshots")
    .select({ filterByFormula: `AND({client_id} = '${clientId}', {month} = '${month}')` })
    .firstPage();

  if (existing.length > 0) {
    await base("MonthlySnapshots").update(existing[0].id, data as Airtable.FieldSet);
  } else {
    await base("MonthlySnapshots").create({
      client_id: [clientId],
      month,
      ...data,
    } as Airtable.FieldSet);
  }
}
