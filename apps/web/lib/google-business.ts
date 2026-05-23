/**
 * Google My Business API (Business Profile API) client.
 * Uses a service account or OAuth2 token stored per client.
 * Pulls current rating and recent review count for the report page.
 */

const GMB_BASE = "https://mybusinessbusinessinformation.googleapis.com/v1";

export interface GmbRating {
  rating: number;
  review_count: number;
}

export async function getGmbRating(
  locationName: string, // "accounts/{accountId}/locations/{locationId}"
  accessToken: string
): Promise<GmbRating> {
  const res = await fetch(`${GMB_BASE}/${locationName}?readMask=rating,userRatingCount`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error(`GMB fetch failed: ${res.status}`);
  const data = await res.json();
  return {
    rating: data.rating ?? 0,
    review_count: data.userRatingCount ?? 0,
  };
}
