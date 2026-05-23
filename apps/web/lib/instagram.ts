/**
 * Instagram Basic Display API client.
 * Each client has their own long-lived access token stored in Airtable.
 * Token lifespan: 60 days — refresh monthly when generating reports.
 */

const IG_BASE = "https://graph.instagram.com";

export interface IgMediaItem {
  id: string;
  timestamp: string;
  like_count: number;
  comments_count: number;
  media_url: string;
  media_type: string;
  reach?: number;
}

export interface IgProfile {
  followers_count: number;
  media_count: number;
  username: string;
}

export async function getIgProfile(accessToken: string): Promise<IgProfile> {
  const res = await fetch(
    `${IG_BASE}/me?fields=followers_count,media_count,username&access_token=${accessToken}`
  );
  if (!res.ok) throw new Error(`IG profile fetch failed: ${res.status}`);
  return res.json();
}

export async function getRecentMedia(
  accessToken: string,
  limit = 12
): Promise<IgMediaItem[]> {
  const fields = "id,timestamp,like_count,comments_count,media_url,media_type";
  const res = await fetch(
    `${IG_BASE}/me/media?fields=${fields}&limit=${limit}&access_token=${accessToken}`
  );
  if (!res.ok) throw new Error(`IG media fetch failed: ${res.status}`);
  const data: { data: IgMediaItem[] } = await res.json();
  return data.data ?? [];
}

export async function refreshLongLivedToken(token: string): Promise<string> {
  const res = await fetch(
    `${IG_BASE}/refresh_access_token?grant_type=ig_refresh_token&access_token=${token}`
  );
  if (!res.ok) throw new Error("token refresh failed");
  const data: { access_token: string } = await res.json();
  return data.access_token;
}
