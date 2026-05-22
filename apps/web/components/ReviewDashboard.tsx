"use client";

import { useState } from "react";
import Image from "next/image";
import type { Lead, ImageVariant } from "@/lib/airtable";

interface Props {
  lead: Lead;
  variants: ImageVariant[];
}

export default function ReviewDashboard({ lead, variants }: Props) {
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "skipped">("idle");
  const [selectedUrl, setSelectedUrl] = useState<string>(variants[0]?.s3_url ?? "");
  const competitors: { name: string; ig: string; posts_per_week: number; rating: number }[] =
    JSON.parse(lead.competitors_json || "[]");

  async function approve() {
    if (!selectedUrl) return;
    setStatus("loading");
    await fetch("/api/leads/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        leadId: lead.id,
        approvedImageUrl: selectedUrl,
        businessName: lead.name,
      }),
    });
    setStatus("done");
  }

  async function skip() {
    setStatus("loading");
    await fetch(`/api/leads/${lead.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pipeline_status: "skipped" }),
    });
    setStatus("skipped");
  }

  async function regenerate() {
    setStatus("loading");
    const pipelineUrl = process.env.NEXT_PUBLIC_PIPELINE_SERVICE_URL;
    await fetch(`${pipelineUrl}/leads/${lead.id}/regenerate`, { method: "POST" });
    setStatus("idle");
    window.location.reload();
  }

  if (status === "done") {
    return (
      <div className="rounded-xl border bg-green-50 p-6 text-green-800">
        ✓ {lead.name} approved — landing page and email sequence triggered.
      </div>
    );
  }

  if (status === "skipped") {
    return (
      <div className="rounded-xl border bg-gray-100 p-6 text-gray-500">
        ✗ {lead.name} skipped.
      </div>
    );
  }

  const bestVariant = [...variants].sort((a, b) => b.avg_score - a.avg_score)[0];

  return (
    <div className="rounded-xl border bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between border-b p-5">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{lead.name}</h2>
          <p className="text-sm text-gray-500">{lead.address}</p>
        </div>
        <div className="flex gap-3 text-sm">
          <span className="rounded-full bg-yellow-100 px-3 py-1 font-medium text-yellow-800">
            Score {lead.score}
          </span>
          <span className="rounded-full bg-red-100 px-3 py-1 font-medium text-red-700">
            {lead.ig_days_inactive}d inactive
          </span>
        </div>
      </div>

      <div className="p-5">
        {/* Image variants */}
        <div className="mb-6 grid grid-cols-3 gap-4">
          {variants.map((v) => (
            <button
              key={v.id}
              onClick={() => setSelectedUrl(v.s3_url)}
              className={`relative overflow-hidden rounded-lg border-2 transition ${
                selectedUrl === v.s3_url
                  ? "border-blue-500 ring-2 ring-blue-200"
                  : "border-transparent hover:border-gray-300"
              }`}
            >
              <Image
                src={v.s3_url}
                alt={`Variant ${v.variant_number}`}
                width={320}
                height={320}
                className="aspect-square w-full object-cover"
              />
              <div className="absolute bottom-0 left-0 right-0 bg-black/60 p-2 text-center">
                <span
                  className={`text-xs font-bold ${
                    v.verdict === "PASS" ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {v.verdict === "PASS" ? "✓" : "✗"} {v.avg_score.toFixed(1)} avg
                </span>
                {v.id === bestVariant?.id && (
                  <span className="ml-2 text-xs text-yellow-300">★ best</span>
                )}
              </div>
            </button>
          ))}
        </div>

        {/* AI note */}
        {bestVariant && (
          <p className="mb-4 rounded bg-blue-50 px-4 py-2 text-sm text-blue-700">
            AI note: best avg {bestVariant.avg_score.toFixed(1)} on variant {bestVariant.variant_number}
          </p>
        )}

        {/* Competitor table */}
        {competitors.length > 0 && (
          <table className="mb-6 w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400">
                <th className="pb-2 font-normal">Business</th>
                <th className="pb-2 font-normal">Posts/wk</th>
                <th className="pb-2 font-normal">Rating</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr className="font-medium">
                <td className="py-1">{lead.name} ← you</td>
                <td className="py-1 text-red-500">
                  last post {lead.ig_days_inactive}d ago ⚠
                </td>
                <td className="py-1">{lead.google_rating} ★</td>
              </tr>
              {competitors.map((c, i) => (
                <tr key={i} className="text-gray-600">
                  <td className="py-1">{c.name}</td>
                  <td className="py-1">{c.posts_per_week}/wk ✓</td>
                  <td className="py-1">{c.rating} ★</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={approve}
            disabled={!selectedUrl || status === "loading"}
            className="flex-1 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            {status === "loading" ? "…" : "✓ Approve selected"}
          </button>
          <button
            onClick={regenerate}
            disabled={status === "loading"}
            className="rounded-lg border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            ↺ Regenerate
          </button>
          <button
            onClick={skip}
            disabled={status === "loading"}
            className="rounded-lg border px-4 py-2 text-sm font-medium text-red-500 hover:bg-red-50 disabled:opacity-50"
          >
            ✗ Skip
          </button>
        </div>
      </div>
    </div>
  );
}
