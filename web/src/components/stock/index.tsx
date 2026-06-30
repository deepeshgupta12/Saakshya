"use client";
/* Stock domain components — docs/08 §5. No entry/target/SL. */

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, TrendingDown, AlertTriangle, Shield } from "lucide-react";
import { Card, CardHeader, CardTitle, Badge, Chip, Skeleton, ErrorState } from "@/components/ui";
import { GroundingBadge, NotAdviceBanner } from "@/components/compliance";
import { EvidenceDrawer } from "@/components/scanner";
import { cn } from "@/lib/utils";
import { formatPrice, signedPercent, formatNumber } from "@/lib/format";
import { aiReveal, riskPulse, staggerContainer, staggerRow, useMotion } from "@/lib/motion/variants";
import type { StockOverview, StockTechnicals, AiSummary } from "@/types";

/* ── StockHeader — JetBrains Mono for price/change ── */
export function StockHeader({
  symbol,
  sessionDate,
  close,
  changePct,
  sector,
  scannerMemberships,
}: {
  symbol: string;
  sessionDate?: string;
  close?: number | null;
  changePct?: number | null;
  sector?: string;
  scannerMemberships?: string[];
}) {
  const isPositive = (changePct ?? 0) >= 0;
  return (
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
      <div>
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-2xl font-bold text-[--text-primary] tracking-tight font-mono">{symbol}</h1>
          {sector && <Badge>{sector}</Badge>}
        </div>
        {sessionDate && (
          <p className="text-xs text-[--text-muted] mt-1 font-mono">
            As of {new Date(sessionDate).toLocaleDateString("en-IN", {
              day: "numeric", month: "short", year: "numeric",
            })}
          </p>
        )}
        {scannerMemberships?.length ? (
          <div className="flex flex-wrap gap-1 mt-2">
            {scannerMemberships.map((s) => (
              <Badge key={s} variant="accent" className="text-[10px]">
                {s.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        ) : null}
      </div>

      <div className="text-right sm:text-right shrink-0">
        {close != null ? (
          <>
            <p className="text-3xl font-bold tabular-nums text-[--text-primary] font-mono tracking-tight">
              {formatPrice(close)}
            </p>
            {changePct != null && (
              <p className={cn(
                "flex items-center justify-end gap-1 text-sm font-medium tabular-nums font-mono mt-0.5",
                isPositive ? "text-[--bullish]" : "text-[--bearish]"
              )}>
                {isPositive
                  ? <TrendingUp className="h-3.5 w-3.5 shrink-0" aria-hidden />
                  : <TrendingDown className="h-3.5 w-3.5 shrink-0" aria-hidden />
                }
                <span>{signedPercent(changePct)}</span>
              </p>
            )}
          </>
        ) : (
          <p className="text-[--text-muted] text-sm">Price unavailable</p>
        )}
      </div>
    </div>
  );
}

/* ── ScannerMembershipChips ── */
export function ScannerMembershipChips({ memberships }: { memberships: string[] }) {
  if (!memberships.length) return null;
  return (
    <div>
      <p className="text-[10px] uppercase tracking-widest text-[--text-muted] mb-2">Appears in scanners</p>
      <div className="flex flex-wrap gap-1.5">
        {memberships.map((m) => (
          <Chip key={m} className="text-[--accent] text-[10px]">
            {m.replace(/_/g, " ")}
          </Chip>
        ))}
      </div>
    </div>
  );
}

/* ── KeyStats — JetBrains Mono values ── */
export function KeyStats({ overview }: { overview: StockOverview }) {
  const stats = [
    { label: "Open",       value: formatPrice(overview.open) },
    { label: "High",       value: formatPrice(overview.high) },
    { label: "Low",        value: formatPrice(overview.low) },
    { label: "Volume",     value: overview.volume != null ? formatNumber(overview.volume) : "—" },
    { label: "Delivery %", value: overview.delivery_pct != null ? `${overview.delivery_pct.toFixed(2)}%` : "—" },
  ];
  return (
    <motion.div
      className="grid grid-cols-2 sm:grid-cols-3 gap-2"
      variants={staggerContainer(0.04)}
      initial="hidden"
      animate="visible"
    >
      {stats.map(({ label, value }) => (
        <motion.div
          key={label}
          variants={staggerRow}
          className="rounded-[--radius-md] bg-[--surface-2] border border-[--border-subtle] px-3 py-2.5"
        >
          <p className="text-[10px] text-[--text-muted] uppercase tracking-wide">{label}</p>
          <p className="text-sm font-semibold tabular-nums text-[--text-primary] font-mono mt-0.5">{value}</p>
        </motion.div>
      ))}
    </motion.div>
  );
}

/* ── IndicatorPanel — JetBrains Mono values ── */
export function IndicatorPanel({ tech }: { tech: StockTechnicals }) {
  type Indicator = { label: string; value: number | null | undefined };
  const indicators: Indicator[] = [
    { label: "RSI (14)",     value: tech.rsi_14 as number | null },
    { label: "MACD",         value: tech.macd as number | null },
    { label: "MACD Signal",  value: tech.macd_signal as number | null },
    { label: "BB Upper",     value: tech.bb_upper as number | null },
    { label: "BB Middle",    value: tech.bb_middle as number | null },
    { label: "BB Lower",     value: tech.bb_lower as number | null },
    { label: "ATR (14)",     value: tech.atr_14 as number | null },
    { label: "SMA 20",       value: tech.sma_20 as number | null },
    { label: "SMA 50",       value: tech.sma_50 as number | null },
    { label: "SMA 200",      value: tech.sma_200 as number | null },
    { label: "Vol Ratio",    value: tech.volume_ratio_20d as number | null },
  ].filter((i) => i.value != null);

  if (!indicators.length) {
    return <p className="text-sm text-[--text-muted]">Technical indicators not available.</p>;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {indicators.map(({ label, value }) => (
        <div
          key={label}
          className="rounded-[--radius-md] bg-[--surface-2] border border-[--border-subtle] px-3 py-2.5"
        >
          <p className="text-[10px] text-[--text-muted] uppercase tracking-wide">{label}</p>
          <p className="text-sm font-semibold tabular-nums text-[--text-primary] font-mono mt-0.5">
            {formatNumber(value, 2)}
          </p>
        </div>
      ))}
    </div>
  );
}

/* ── AiStockSummaryCard — aiReveal animation, violet left-rule ── docs/07 §2.7 */
export function AiStockSummaryCard({
  aiSummary,
  isLoading,
  isError,
  suppressed,
}: {
  aiSummary?: AiSummary;
  isLoading?: boolean;
  isError?: boolean;
  suppressed?: boolean;
}) {
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const { reduced } = useMotion();

  if (isLoading) return <Skeleton className="h-40" />;
  if (isError)   return <ErrorState message="AI summary unavailable. Try refreshing." />;

  if (suppressed || !aiSummary) {
    return (
      <Card className="border-l-[3px] border-l-[--ai]">
        <CardHeader>
          <CardTitle>AI Stock Summary</CardTitle>
          <Badge variant="ai" aria-label="AI-generated content">AI</Badge>
        </CardHeader>
        <p className="text-sm text-[--text-muted] italic">
          AI summary unavailable — required inputs are missing.
        </p>
        <NotAdviceBanner className="mt-4" />
      </Card>
    );
  }

  return (
    <>
      <Card className="border-l-[3px] border-l-[--ai] relative overflow-hidden">
        {/* Violet radial glow — subtle depth */}
        <div
          className="pointer-events-none absolute inset-0 rounded-[inherit]"
          style={{ background: "radial-gradient(ellipse at top left, rgba(154,123,255,0.07) 0%, transparent 65%)" }}
          aria-hidden
        />

        <CardHeader>
          <CardTitle>AI Stock Summary</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="ai" aria-label="AI-generated content">AI</Badge>
            {aiSummary.model_version && (
              <span className="text-[10px] text-[--text-muted] font-mono">{aiSummary.model_version}</span>
            )}
          </div>
        </CardHeader>

        <motion.div
          variants={aiReveal}
          initial={reduced ? "visible" : "hidden"}
          animate="visible"
        >
          <p className="text-sm text-[--text-secondary] leading-relaxed">{aiSummary.summary}</p>

          {aiSummary.risk_notes?.length > 0 && (
            <div className="mt-3 space-y-1.5">
              {aiSummary.risk_notes.map((note, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-[--warning]">
                  <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" aria-hidden />
                  <span>{note}</span>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        <div className="mt-4 flex flex-col gap-2">
          <GroundingBadge onViewEvidence={() => setDrawerOpen(true)} />
          <NotAdviceBanner />
        </div>
      </Card>

      <EvidenceDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        symbol={aiSummary.symbol}
        facts={aiSummary.cited_facts as Array<{ field: string; value: unknown; label?: string }>}
        riskFlags={aiSummary.risk_notes}
        asOf={aiSummary.session_date}
      />
    </>
  );
}

/* ── RiskBadge — one-shot amber pulse on first render ── */
export function RiskBadge({ riskFlags }: { riskFlags?: string[] }) {
  const { reduced } = useMotion();
  if (!riskFlags?.length) return null;
  return (
    <motion.div
      className="flex items-center gap-2 rounded-[--radius-md] border border-[--warning]/30 bg-[--warning]/5 px-3 py-2"
      variants={riskPulse}
      initial={reduced ? "pulse" : "initial"}
      animate="pulse"
    >
      <AlertTriangle className="h-3.5 w-3.5 text-[--warning] shrink-0" aria-hidden />
      <p className="text-xs text-[--warning] font-medium">{riskFlags[0]}</p>
      {riskFlags.length > 1 && (
        <span className="text-[10px] text-[--text-muted] ml-auto">
          +{riskFlags.length - 1} more
        </span>
      )}
    </motion.div>
  );
}

/* ── StockSkeleton ── */
export function StockSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex justify-between gap-4">
        <Skeleton className="h-12 w-40" />
        <Skeleton className="h-12 w-32" />
      </div>
      <Skeleton className="h-72 w-full rounded-[--radius-lg]" />
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[1,2,3,4,5].map((i) => <Skeleton key={i} className="h-14" />)}
      </div>
      <Skeleton className="h-40" />
    </div>
  );
}
