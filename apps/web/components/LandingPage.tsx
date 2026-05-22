"use client";

import { useState } from "react";
import Image from "next/image";
import type { Lead, ImageVariant } from "@/lib/airtable";

interface Props {
  lead: Lead;
  variants: ImageVariant[];
}

export default function LandingPage({ lead, variants }: Props) {
  const [form, setForm] = useState({ name: "", email: "" });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const competitors: { name: string; posts_per_week: number; rating: number }[] = JSON.parse(
    lead.competitors_json || "[]"
  );

  const areaAvgRating =
    competitors.length > 0
      ? (competitors.reduce((s, c) => s + c.rating, 0) / competitors.length).toFixed(1)
      : null;

  const primary = lead.brand_primary_hex || "#C4A882";
  const secondary = lead.brand_secondary_hex || "#2C2C2C";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    await fetch(`/api/leads/${lead.id}/cta`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setLoading(false);
    setSubmitted(true);
  }

  return (
    <main className="min-h-screen bg-white font-sans">
      {/* Hero */}
      <div
        className="px-6 py-10 text-center"
        style={{ background: `linear-gradient(135deg, ${primary}22, ${secondary}11)` }}
      >
        {lead.brand_logo_url && (
          <Image
            src={lead.brand_logo_url}
            alt={lead.name}
            width={120}
            height={60}
            className="mx-auto mb-4 h-12 w-auto object-contain"
          />
        )}
        <p className="text-sm font-medium uppercase tracking-widest text-gray-500">
          Here&apos;s what your Instagram could look like
        </p>
        <h1 className="mt-2 text-3xl font-bold text-gray-900">{lead.name}</h1>
      </div>

      {/* Image grid */}
      <div className="mx-auto max-w-2xl px-6 py-8">
        <div className="grid grid-cols-3 gap-3">
          {variants.slice(0, 3).map((v) => (
            <div key={v.id} className="overflow-hidden rounded-xl shadow-sm">
              <Image
                src={v.s3_url}
                alt="Instagram post preview"
                width={320}
                height={320}
                className="aspect-square w-full object-cover"
              />
            </div>
          ))}
        </div>
        <p className="mt-3 text-center text-xs text-gray-400">
          Branded posts made specifically for {lead.name}
        </p>
      </div>

      {/* Competitor table */}
      <div className="mx-auto max-w-2xl px-6 pb-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
          Your IG vs {lead.address.split(",")[1]?.trim() ?? "local"} competitors
        </h2>
        <div className="overflow-hidden rounded-xl border">
          <table className="w-full text-sm">
            <tbody>
              <tr className="border-b bg-yellow-50">
                <td className="px-4 py-3 font-medium text-gray-900">{lead.name}</td>
                <td className="px-4 py-3 text-red-600">
                  Last post: {lead.ig_days_inactive} days ago ⚠️
                </td>
                <td className="px-4 py-3 text-gray-600">{lead.google_rating} ★</td>
              </tr>
              {competitors.map((c, i) => (
                <tr key={i} className={i < competitors.length - 1 ? "border-b" : ""}>
                  <td className="px-4 py-3 text-gray-700">{c.name}</td>
                  <td className="px-4 py-3 text-green-600">{c.posts_per_week} posts/week ✓</td>
                  <td className="px-4 py-3 text-gray-600">{c.rating} ★</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {areaAvgRating && (
          <p className="mt-2 text-xs text-gray-400">
            Google Rating: {lead.google_rating} ★ &nbsp;•&nbsp; Area average: {areaAvgRating} ★
          </p>
        )}
      </div>

      {/* CTA */}
      <div className="mx-auto max-w-2xl px-6 pb-16">
        <div
          className="rounded-2xl p-8 text-center"
          style={{ backgroundColor: `${primary}18`, border: `1px solid ${primary}44` }}
        >
          {submitted ? (
            <>
              <p className="text-2xl">🎉</p>
              <p className="mt-2 text-lg font-semibold text-gray-900">
                You&apos;re on the list!
              </p>
              <p className="mt-1 text-sm text-gray-500">
                Mike will be in touch within the hour.
              </p>
            </>
          ) : (
            <>
              <h3 className="text-xl font-bold text-gray-900">
                Yes, I want this for my business
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                Enter your details and Mike will reach out within the hour.
              </p>
              <form onSubmit={handleSubmit} className="mt-4 space-y-3">
                <input
                  type="text"
                  required
                  placeholder="Your name"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full rounded-lg border px-4 py-2 text-sm outline-none focus:border-gray-400"
                />
                <input
                  type="email"
                  required
                  placeholder="Your email"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  className="w-full rounded-lg border px-4 py-2 text-sm outline-none focus:border-gray-400"
                />
                <button
                  type="submit"
                  disabled={loading}
                  style={{ backgroundColor: primary }}
                  className="w-full rounded-lg py-3 text-sm font-bold text-white transition hover:opacity-90 disabled:opacity-50"
                >
                  {loading ? "Sending…" : "YES, I WANT THIS FOR MY BUSINESS"}
                </button>
              </form>
            </>
          )}
        </div>
        <p className="mt-4 text-center text-xs text-gray-400">
          Questions? Reply to Mike&apos;s email or call{" "}
          <a href={`tel:${process.env.NEXT_PUBLIC_OWNER_PHONE}`} className="underline">
            {process.env.NEXT_PUBLIC_OWNER_PHONE}
          </a>
        </p>
      </div>
    </main>
  );
}
