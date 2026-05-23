"use client";

import Image from "next/image";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts";
import type { Lead, Client, MonthlySnapshot, ImageVariant } from "@/lib/airtable";
import type { IgProfile, IgMediaItem } from "@/lib/instagram";
import type { GmbRating } from "@/lib/google-business";

interface Props {
  lead: Lead;
  client: Client;
  snapshots: MonthlySnapshot[];
  igProfile: IgProfile | null;
  recentMedia: IgMediaItem[];
  gmbRating: GmbRating | null;
  approvedVariants: ImageVariant[];
  competitors: { name: string; posts_per_week: number; rating: number }[];
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border bg-white p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-400">{label}</p>
      <p className="mt-1 text-3xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-1 text-sm text-green-600">{sub}</p>}
    </div>
  );
}

export default function ReportPage({
  lead,
  client,
  snapshots,
  igProfile,
  recentMedia,
  gmbRating,
  approvedVariants,
  competitors,
}: Props) {
  const currentMonth = new Date().toLocaleString("default", { month: "long", year: "numeric" });

  // derived stats
  const latestSnap = snapshots[snapshots.length - 1];
  const prevSnap = snapshots[snapshots.length - 2];

  const currentFollowers = igProfile?.followers_count ?? latestSnap?.followers ?? lead.ig_followers;
  const followerGrowth =
    prevSnap && currentFollowers > prevSnap.followers
      ? `+${currentFollowers - prevSnap.followers} (+${(
          ((currentFollowers - prevSnap.followers) / prevSnap.followers) *
          100
        ).toFixed(1)}%)`
      : null;

  const currentRating = gmbRating?.rating ?? latestSnap?.google_rating ?? lead.google_rating;
  const ratingGrowth =
    prevSnap && currentRating > prevSnap.google_rating
      ? `+${(currentRating - prevSnap.google_rating).toFixed(1)} this month`
      : null;

  const postsDelivered = latestSnap?.posts_delivered ?? 0;

  const topPost = recentMedia.length
    ? [...recentMedia].sort((a, b) => b.like_count - a.like_count)[0]
    : null;

  const sparkData = snapshots.map((s) => ({
    month: s.month.slice(5),
    followers: s.followers,
  }));
  if (igProfile && (!latestSnap || latestSnap.month !== _currentMonth())) {
    sparkData.push({ month: _currentMonth().slice(5), followers: igProfile.followers_count });
  }

  return (
    <main className="min-h-screen bg-gray-50 p-6 pb-20">
      <div className="mx-auto max-w-3xl space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{lead.name}</h1>
            <p className="text-sm text-gray-500">Monthly Report — {currentMonth}</p>
          </div>
          {lead.brand_logo_url && (
            <Image
              src={lead.brand_logo_url}
              alt={lead.name}
              width={80}
              height={40}
              className="h-10 w-auto object-contain"
            />
          )}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat
            label="Followers"
            value={currentFollowers.toLocaleString()}
            sub={followerGrowth ?? undefined}
          />
          <Stat
            label="Posts delivered"
            value={`${postsDelivered} / 12`}
            sub={postsDelivered === 12 ? "✓ Full month" : undefined}
          />
          <Stat
            label="Google rating"
            value={`${currentRating} ★`}
            sub={ratingGrowth ?? undefined}
          />
          <Stat
            label="Monthly fee"
            value={`$${client.monthly_fee}`}
            sub="Active"
          />
        </div>

        {/* Follower sparkline */}
        {sparkData.length > 1 && (
          <div className="rounded-2xl border bg-white p-5">
            <p className="mb-4 text-sm font-semibold text-gray-700">Follower growth</p>
            <ResponsiveContainer width="100%" height={120}>
              <LineChart data={sparkData}>
                <XAxis dataKey="month" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  formatter={(v: number) => [v.toLocaleString(), "Followers"]}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />
                <Line
                  type="monotone"
                  dataKey="followers"
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Top performing post */}
        {topPost && (
          <div className="rounded-2xl border bg-white p-5">
            <p className="mb-4 text-sm font-semibold text-gray-700">Top performing post</p>
            <div className="flex gap-4">
              <div className="relative h-28 w-28 flex-shrink-0 overflow-hidden rounded-xl">
                <Image
                  src={topPost.media_url}
                  alt="Top post"
                  fill
                  className="object-cover"
                />
              </div>
              <div className="flex flex-col justify-center gap-2">
                <div className="flex gap-4 text-sm text-gray-700">
                  <span>❤️ {topPost.like_count} likes</span>
                  <span>💬 {topPost.comments_count} comments</span>
                  {topPost.reach && <span>👁 {topPost.reach} reach</span>}
                </div>
                <p className="text-xs text-gray-400">
                  Posted {new Date(topPost.timestamp).toLocaleDateString("en-AU")}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Competitor tracker */}
        <div className="rounded-2xl border bg-white p-5">
          <p className="mb-4 text-sm font-semibold text-gray-700">Competitor tracker</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400">
                <th className="pb-2 font-normal">Business</th>
                <th className="pb-2 font-normal">Google ★</th>
                <th className="pb-2 font-normal">Posts/wk</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {competitors.map((c, i) => (
                <tr key={i}>
                  <td className="py-2 text-gray-700">{c.name}</td>
                  <td className="py-2 text-gray-600">{c.rating} ★</td>
                  <td className="py-2 text-gray-600">{c.posts_per_week}/wk</td>
                </tr>
              ))}
              <tr className="font-semibold">
                <td className="py-2 text-gray-900">{lead.name} ← you</td>
                <td className="py-2 text-gray-900">{currentRating} ★</td>
                <td className="py-2 text-gray-900">3/wk</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Next month preview */}
        {approvedVariants.length > 0 && (
          <div className="rounded-2xl border bg-white p-5">
            <p className="mb-4 text-sm font-semibold text-gray-700">Next month preview</p>
            <div className="grid grid-cols-3 gap-3">
              {approvedVariants.map((v) => (
                <div key={v.id} className="overflow-hidden rounded-xl">
                  <Image
                    src={v.s3_url}
                    alt="Upcoming post"
                    width={200}
                    height={200}
                    className="aspect-square w-full object-cover"
                  />
                </div>
              ))}
            </div>
            <button className="mt-4 w-full rounded-xl border border-gray-200 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              Approve next month&apos;s content →
            </button>
          </div>
        )}

        <p className="text-center text-xs text-gray-300">
          Powered by your agency &nbsp;·&nbsp; {new Date().getFullYear()}
        </p>
      </div>
    </main>
  );
}

function _currentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}
