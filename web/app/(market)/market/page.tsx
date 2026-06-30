/* Market dashboard — /market (docs/08 §2). ISR, revalidated post-EOD batch.
   Server-renders the page; client components handle interactivity. */

import { Suspense } from "react";
import type { Metadata } from "next";
import { MarketDashboardClient } from "./MarketDashboardClient";
import { NotAdviceBanner } from "@/components/compliance";

export const metadata: Metadata = {
  title: "Market Dashboard — Saakshya",
  description:
    "EOD market state: indices, breadth, sector momentum, and AI-grounded market summary. Not investment advice.",
};

/* ISR: revalidate 8 hours (post-EOD batch triggers on-demand via /api/internal/revalidate) */
export const revalidate = 28800;

export default function MarketPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[--text-primary]">Market Dashboard</h1>
          <p className="text-sm text-[--text-muted]">End-of-day analytics · not investment advice</p>
        </div>
        <NotAdviceBanner className="hidden sm:flex max-w-sm shrink-0" />
      </div>

      <Suspense fallback={<MarketLoadingSkeleton />}>
        <MarketDashboardClient />
      </Suspense>
    </div>
  );
}

function MarketLoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="flex gap-3">
        {[1,2,3,4].map((i) => <div key={i} className="h-10 w-28 rounded-[--radius-md] bg-[--surface-3]" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="h-32 lg:col-span-2 rounded-[--radius-lg] bg-[--surface-3]" />
        <div className="h-32 rounded-[--radius-lg] bg-[--surface-3]" />
      </div>
      <div className="h-48 rounded-[--radius-lg] bg-[--surface-3]" />
    </div>
  );
}
