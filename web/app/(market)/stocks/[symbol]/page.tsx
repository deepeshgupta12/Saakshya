/* Stock detail page — /stocks/[symbol] (docs/08 §5).
   No entry/target/SL — RA-gated → RaGatedPlaceholder. */

import { redirect } from "next/navigation";
import type { Metadata } from "next";
import { StockDetailClient } from "./StockDetailClient";
import { NotAdviceBanner, RaGatedPlaceholder } from "@/components/compliance";

type Props = { params: Promise<{ symbol: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  const sym = symbol.toUpperCase();
  return {
    title: `${sym} — Saakshya`,
    description: `Evidence-based analytics for ${sym}. Scanner signals, technical indicators, and AI-grounded summary. Not investment advice.`,
  };
}

export default async function StockDetailPage({ params }: Props) {
  const { symbol } = await params;
  const sym = symbol.toUpperCase();

  /* 301 to uppercase canonical — docs/05 §6 */
  if (symbol !== sym) redirect(`/stocks/${sym}`);

  return (
    <div className="space-y-6">
      <NotAdviceBanner />
      <StockDetailClient symbol={sym} />

      {/* RA-gated placeholder — NEVER an empty levels widget */}
      <RaGatedPlaceholder label="Entry / Target / Stop-Loss" />
    </div>
  );
}
