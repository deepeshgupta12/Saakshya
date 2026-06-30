/* Scanner detail page — /scanners/[slug] (docs/08 §4).
   Shared template for momentum, volume-breakout, rsi, moving-average, etc. */

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ScannerDetailClient } from "./ScannerDetailClient";
import { NotAdviceBanner } from "@/components/compliance";

/* Canonical scanner slugs — docs/05 §2 */
const VALID_SLUGS = new Set([
  "momentum", "volume-breakout", "rsi", "moving-average",
  "breakout", "breakdown", "sector-strength",
  "near-52-week-high", "200-dma-reclaim", "oversold-recovery",
]);

const SCANNER_META: Record<string, { label: string; description: string; validationNote?: string }> = {
  "momentum":           { label: "Momentum", description: "Stocks with strong price momentum across multiple timeframes, confirmed by volume.", validationNote: "Score validated against historical momentum persistence (docs/13)." },
  "volume-breakout":    { label: "Volume Breakout", description: "Stocks with significantly elevated volume relative to their 20-day average." },
  "rsi":                { label: "RSI", description: "Stocks in distinct RSI zones: oversold (<30) or overbought (>70) relative to recent history." },
  "moving-average":     { label: "Moving Average", description: "Stocks showing price/MA crossover or significant deviation from key moving averages." },
  "breakout":           { label: "Breakout", description: "Stocks breaking above recent price consolidation ranges with volume confirmation. False breakouts shown as risk flags." },
  "breakdown":          { label: "Breakdown", description: "Stocks breaking below support levels. Descriptive state — not a sell signal." },
  "sector-strength":    { label: "Sector Strength", description: "Leading sectors by relative-strength across the universe." },
  "near-52-week-high":  { label: "Near 52-Week High", description: "Stocks within 5% of their 52-week high. Descriptive proximity measure." },
  "200-dma-reclaim":    { label: "200-DMA Reclaim", description: "Stocks reclaiming their 200-day moving average from below — a notable crossover state." },
  "oversold-recovery":  { label: "Oversold Recovery", description: "Stocks exiting oversold RSI territory. Descriptive state — not a buy signal." },
};

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const meta = SCANNER_META[slug];
  if (!meta) return { title: "Scanner — Saakshya" };
  return {
    title: `${meta.label} Scanner — Saakshya`,
    description: `${meta.description} Evidence-based scanner results, not investment advice.`,
  };
}

export default async function ScannerDetailPage({ params }: Props) {
  const { slug } = await params;
  if (!VALID_SLUGS.has(slug)) notFound();

  const meta = SCANNER_META[slug] ?? { label: slug, description: "" };

  return (
    <div className="space-y-6">
      <NotAdviceBanner />
      <ScannerDetailClient
        slug={slug}
        label={meta.label}
        description={meta.description}
        validationNote={meta.validationNote}
      />
    </div>
  );
}
