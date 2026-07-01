"use client";
/* Market domain components — docs/08 §2. Descriptive analytics, no advisory language. */

import * as React from "react";
import Link from "next/link";
import { motion, animate, useMotionValue, useTransform } from "framer-motion";
import { TrendingUp, TrendingDown, Activity } from "lucide-react";
import { Card, CardHeader, CardTitle, Badge, Skeleton, ErrorState, EmptyState } from "@/components/ui";
import { NotAdviceBanner, GroundingBadge } from "@/components/compliance";
import { cn } from "@/lib/utils";
import { formatNumber, signedPercent } from "@/lib/format";
import {
  staggerContainer, staggerTile, staggerRow, aiReveal, spring, useMotion,
} from "@/lib/motion/variants";
import type { MarketSummary, SectorSummary } from "@/types";

/* ── IndexStrip — scanner count pills ── */
export function IndexStrip({ summary }: { summary: MarketSummary }) {
  return (
    <motion.div
      className="flex flex-wrap gap-3"
      variants={staggerContainer(0.04)}
      initial="hidden"
      animate="visible"
    >
      {Object.entries(summary.scanner_counts).map(([scanner, { count, label }]) => (
        <motion.div key={scanner} variants={staggerRow}>
          <Link
            href={`/scanners/${scanner.replace(/_/g, "-")}`}
            className={cn(
              "flex items-center gap-2 rounded-(--radius-md) border border-(--border-subtle)",
              "bg-(--surface-2) px-3 py-2 text-xs",
              "hover:border-(--border-strong) hover:bg-(--surface-3)",
              "transition-all duration-(--motion-fast) cursor-pointer"
            )}
          >
            <span className="text-(--text-muted) capitalize">
              {(label || scanner).replace(/_/g, " ")}
            </span>
            <span className="font-mono font-semibold tabular-nums text-(--accent)">{count}</span>
          </Link>
        </motion.div>
      ))}
    </motion.div>
  );
}

/* ── BreadthPanel — with count-up on mount ── */
export function BreadthPanel({ summary }: { summary: MarketSummary }) {
  const total = summary.total_members || 1;
  const adv = summary.advance_count;
  const dec = summary.decline_count;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Market Breadth</CardTitle>
        <Activity className="h-4 w-4 text-(--text-muted) shrink-0" aria-hidden />
      </CardHeader>
      <div className="flex flex-wrap gap-6">
        <CountUpStat label="Advancing" value={adv} color="text-(--bullish)" Icon={TrendingUp} />
        <CountUpStat label="Declining" value={dec} color="text-(--bearish)" Icon={TrendingDown} />
        <CountUpStat label="Universe" value={total} color="text-(--text-secondary)" />
      </div>
    </Card>
  );
}

function CountUpStat({
  label, value, color, Icon,
}: {
  label: string; value: number; color: string; Icon?: React.ElementType;
}) {
  const { reduced } = useMotion();
  const mv = useMotionValue(reduced ? value : 0);
  const displayed = useTransform(mv, (v) => Math.round(v));

  React.useEffect(() => {
    if (reduced) { mv.set(value); return; }
    const ctrl = animate(mv, value, { duration: 0.8, ease: [0.2, 0.8, 0.2, 1] });
    return ctrl.stop;
  }, [value, reduced, mv]);

  return (
    <div>
      <div className={cn("flex items-center gap-1.5 text-xl font-bold font-mono tabular-nums", color)}>
        {Icon && <Icon className="h-4 w-4 shrink-0" aria-hidden />}
        <motion.span>{displayed}</motion.span>
      </div>
      <p className="text-xs text-(--text-muted) mt-0.5">{label}</p>
    </div>
  );
}

/* ── SectorHeatmap — stagger tile reveal + spring enter ── */
export function SectorHeatmap({ sectors }: { sectors: SectorSummary[] }) {
  return (
    <motion.div
      className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2"
      variants={staggerContainer(0.04)}
      initial="hidden"
      animate="visible"
    >
      {sectors.map((sec) => {
        const pct = sec.change_pct ?? 0;
        const isPositive = pct >= 0;
        return (
          <motion.div key={sec.sector_id} variants={staggerTile}>
            <Link
              href={`/sectors/${sec.slug}`}
              className={cn(
                "block rounded-(--radius-lg) border p-3",
                "hover:shadow-(--shadow-elev-2)",
                "transition-all duration-(--motion-fast) cursor-pointer",
                isPositive
                  ? "border-(--bullish)/20 bg-(--bullish)/5 hover:bg-(--bullish)/10"
                  : "border-(--bearish)/20 bg-(--bearish)/5 hover:bg-(--bearish)/10"
              )}
            >
              <p className="text-xs font-medium text-(--text-primary) leading-tight line-clamp-1">
                {sec.name}
              </p>
              <p className={cn(
                "mt-1 text-sm font-bold font-mono tabular-nums",
                isPositive ? "text-(--bullish)" : "text-(--bearish)"
              )}>
                {isPositive ? "+" : ""}{pct.toFixed(2)}%
              </p>
              {sec.strength_score != null && (
                <p className="mt-0.5 text-[10px] text-(--text-muted) tabular-nums">
                  Score {Math.round(sec.strength_score)}
                </p>
              )}
            </Link>
          </motion.div>
        );
      })}
    </motion.div>
  );
}

/* ── AiMarketSummaryCard — violet left-rule, aiReveal animation ── */
export function AiMarketSummaryCard({
  headline,
  narrative,
  suppressed,
  dataConfidence,
  onViewEvidence,
}: {
  headline?: string;
  narrative?: string;
  suppressed?: boolean;
  dataConfidence?: string;
  onViewEvidence?: () => void;
}) {
  const { reduced } = useMotion();
  return (
    <Card className="border-l-[3px] border-l-(--ai) relative overflow-hidden">
      {/* AI glow accent — subtle, non-distracting */}
      <div
        className="pointer-events-none absolute inset-0 rounded-[inherit]"
        style={{ background: "radial-gradient(ellipse at top left, rgba(154,123,255,0.06) 0%, transparent 65%)" }}
        aria-hidden
      />

      <CardHeader>
        <CardTitle>AI Market Summary</CardTitle>
        <Badge variant="ai" aria-label="AI-generated content">AI</Badge>
      </CardHeader>

      {suppressed ? (
        <p className="text-sm text-(--text-muted) italic">
          Summary unavailable — required market inputs are missing.
        </p>
      ) : (
        <motion.div
          variants={aiReveal}
          initial={reduced ? "visible" : "hidden"}
          animate="visible"
        >
          {headline && (
            <p className="text-sm font-medium text-(--text-primary) mb-2 leading-snug">{headline}</p>
          )}
          {narrative && (
            <p className="text-xs text-(--text-secondary) leading-relaxed">{narrative}</p>
          )}
        </motion.div>
      )}

      <div className="mt-4 flex flex-col gap-2">
        <GroundingBadge onViewEvidence={onViewEvidence} />
        <NotAdviceBanner />
        {dataConfidence && (
          <DataConfidenceIndicator confidence={dataConfidence} />
        )}
      </div>
    </Card>
  );
}

/* ── DataConfidenceIndicator ── */
export function DataConfidenceIndicator({ confidence }: { confidence?: string }) {
  const map: Record<string, { label: string; variant: "bullish" | "neutral" | "bearish" }> = {
    HIGH:   { label: "High confidence",   variant: "bullish" },
    MEDIUM: { label: "Medium confidence", variant: "neutral" },
    LOW:    { label: "Low confidence",    variant: "bearish" },
  };
  const info = map[confidence ?? "MEDIUM"] ?? map.MEDIUM;
  return <Badge variant={info.variant}>{info.label}</Badge>;
}

/* ── MarketMoversTable — descriptive language, cursor-pointer links ── */
interface Mover { symbol: string; change_pct?: number | null; volume?: number | null; }

export function MarketMoversTable({
  title,
  movers,
  emptyText = "No data available",
}: {
  title: string;
  movers: Mover[];
  emptyText?: string;
}) {
  if (!movers.length) return <EmptyState title={emptyText} />;
  return (
    <div>
      <h3 className="text-[10px] font-semibold text-(--text-muted) mb-3 uppercase tracking-wider">
        {title}
      </h3>
      <div className="space-y-0.5">
        {movers.map((m) => {
          const pct = m.change_pct;
          const pos = (pct ?? 0) >= 0;
          return (
            <Link
              key={m.symbol}
              href={`/stocks/${m.symbol}`}
              className={cn(
                "flex items-center justify-between rounded-(--radius-md) px-2 py-2",
                "hover:bg-(--surface-3) transition-colors duration-(--motion-fast) cursor-pointer",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--accent)"
              )}
            >
              <span className="text-sm font-semibold text-(--text-primary) font-mono tracking-wide">
                {m.symbol}
              </span>
              {pct != null && (
                <span className={cn(
                  "text-sm font-medium font-mono tabular-nums",
                  pos ? "text-(--bullish)" : "text-(--bearish)"
                )}>
                  {pos ? "+" : ""}{pct.toFixed(2)}%
                </span>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

/* ── Loading skeletons ── */
export function MarketSkeleton() {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-3">
        {[1,2,3,4].map((i) => <Skeleton key={i} className="h-10 w-28" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Skeleton className="h-32 lg:col-span-2" />
        <Skeleton className="h-32" />
      </div>
      <Skeleton className="h-48" />
    </div>
  );
}
