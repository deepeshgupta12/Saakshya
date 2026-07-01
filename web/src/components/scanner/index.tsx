"use client";
/* Scanner domain components — docs/08 §3–§4. Membership language only. */

import * as React from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, AlertTriangle, X, TrendingUp, TrendingDown } from "lucide-react";
import {
  Card, ScoreBadge, Badge, Chip, Skeleton, EmptyState, ErrorState,
} from "@/components/ui";
import { NotAdviceBanner, GroundingBadge } from "@/components/compliance";
import { cn } from "@/lib/utils";
import { formatPercent, signedPercent } from "@/lib/format";
import {
  staggerContainer, staggerRow, drawerSlideRight, scrimFade, spring, useMotion,
} from "@/lib/motion/variants";
import type { ScannerMeta, ScannerResult } from "@/types";

/* ── ScannerCard (directory) ── */
export function ScannerCard({ scanner }: { scanner: ScannerMeta }) {
  return (
    <Link
      href={`/scanners/${scanner.scanner.replace(/_/g, "-")}`}
      className={cn(
        "group block rounded-(--radius-lg) border border-(--border-subtle)",
        "bg-(--surface-1) p-5",
        "hover:border-(--border-strong) hover:bg-(--surface-2) hover:shadow-(--shadow-elev-2)",
        "transition-all duration-(--motion-base) cursor-pointer",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--accent)"
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="text-sm font-semibold text-(--text-primary) capitalize leading-snug">
          {scanner.label || scanner.scanner.replace(/_/g, " ")}
        </h3>
        <span className="shrink-0 text-xs font-semibold font-mono tabular-nums text-(--accent) bg-(--accent)/10 px-2 py-0.5 rounded-(--radius-sm)">
          {scanner.result_count}
        </span>
      </div>
      {scanner.description && (
        <p className="text-xs text-(--text-muted) line-clamp-2 leading-relaxed">
          {scanner.description}
        </p>
      )}
      {scanner.last_run_at && (
        <p className="mt-2 text-[10px] text-(--text-muted)">
          Last run: {new Date(scanner.last_run_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
        </p>
      )}
      <ChevronRight className="mt-3 h-3.5 w-3.5 text-(--text-muted) opacity-0 group-hover:opacity-100 transition-opacity" aria-hidden />
    </Link>
  );
}

/* ── ScannerHeader ── */
export function ScannerHeader({
  scanner,
  description,
  resultCount,
  asOf,
  validationNote,
}: {
  scanner: string;
  description?: string;
  resultCount?: number;
  asOf?: string;
  validationNote?: string;
}) {
  const label = scanner.replace(/-/g, " ");
  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-xl font-bold text-(--text-primary) capitalize tracking-tight">{label} Scanner</h1>
        {resultCount != null && (
          <Badge variant="accent" className="font-mono tabular-nums">{resultCount} members</Badge>
        )}
        {asOf && (
          <Badge variant="neutral" className="font-mono text-[10px]">As of {asOf}</Badge>
        )}
      </div>
      {description && (
        <p className="mt-2 text-sm text-(--text-muted) leading-relaxed max-w-2xl">{description}</p>
      )}
      {validationNote && (
        <p className="mt-1 text-xs text-(--text-muted) italic opacity-80">{validationNote}</p>
      )}
      <p className="mt-2 text-xs text-(--text-muted)">
        Stocks that appear in this scanner. This is not a recommendation to trade.
      </p>
    </div>
  );
}

/* ── ReasonChips ── */
export function ReasonChips({ reasons }: { reasons: string[] }) {
  if (!reasons.length) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {reasons.map((r) => (
        <Chip key={r} className="text-[10px]">{r}</Chip>
      ))}
    </div>
  );
}

/* ── RiskFlagChip ── */
export function RiskFlagChip({ flag }: { flag: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-(--radius-sm) bg-(--warning)/10 border border-(--warning)/20 px-2 py-0.5 text-[10px] text-(--warning)">
      <AlertTriangle className="h-2.5 w-2.5 shrink-0" aria-hidden />
      {flag}
    </span>
  );
}

/* ── EvidenceDrawer — spring slide-in, AnimatePresence ── docs/07 §2.8 */
interface EvidenceFact { field: string; value: unknown; label?: string; }

export function EvidenceDrawer({
  open,
  onClose,
  symbol,
  facts,
  score,
  reasons,
  riskFlags,
  asOf,
}: {
  open: boolean;
  onClose: () => void;
  symbol: string;
  facts?: EvidenceFact[];
  score?: number;
  reasons?: string[];
  riskFlags?: string[];
  asOf?: string;
}) {
  const { reduced } = useMotion();

  /* Keyboard: Esc to close */
  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Scrim */}
          <motion.div
            key="scrim"
            className="fixed inset-0 z-[var(--z-drawer)] bg-black/55"
            variants={scrimFade}
            initial={reduced ? "visible" : "hidden"}
            animate="visible"
            exit="exit"
            onClick={onClose}
            aria-hidden
          />

          {/* Drawer panel */}
          <motion.aside
            key="drawer"
            role="dialog"
            aria-modal="true"
            aria-label={`Evidence for ${symbol}`}
            className={cn(
              "fixed right-0 top-0 bottom-0 z-[calc(var(--z-drawer)+1)]",
              "w-full max-w-sm",
              "border-l border-(--border-subtle) bg-(--surface-1)",
              "flex flex-col overflow-hidden",
              "shadow-(--shadow-elev-3)"
            )}
            variants={drawerSlideRight}
            initial={reduced ? "visible" : "hidden"}
            animate="visible"
            exit="exit"
          >
            {/* Header — glass */}
            <div className="glass flex items-start justify-between px-5 py-4 border-b border-(--border-subtle) shrink-0">
              <div>
                <h2 className="text-sm font-semibold text-(--text-primary) tracking-tight">
                  Evidence — <span className="font-mono">{symbol}</span>
                </h2>
                {asOf && (
                  <p className="text-[10px] text-(--text-muted) mt-0.5 font-mono">As of {asOf}</p>
                )}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close evidence drawer"
                className={cn(
                  "rounded-(--radius-sm) p-1.5 -mr-1 mt-0.5 shrink-0",
                  "hover:bg-(--surface-3) text-(--text-muted) hover:text-(--text-primary)",
                  "cursor-pointer transition-colors duration-(--motion-fast)",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--accent)"
                )}
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Content scroll */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
              {/* Composite score */}
              {score != null && (
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-(--text-muted) mb-2">
                    Composite Score
                  </p>
                  <ScoreBadge score={score} />
                </div>
              )}

              {/* Signal reasons */}
              {reasons?.length ? (
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-(--text-muted) mb-2">
                    Signal Reasons
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {reasons.map((r) => <Chip key={r}>{r}</Chip>)}
                  </div>
                </div>
              ) : null}

              {/* Risk flags */}
              {riskFlags?.length ? (
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-(--text-muted) mb-2">
                    Risk Flags
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {riskFlags.map((f) => <RiskFlagChip key={f} flag={f} />)}
                  </div>
                </div>
              ) : null}

              {/* Cited data metrics */}
              {facts?.length ? (
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-(--text-muted) mb-2">
                    Cited Data
                  </p>
                  <div className="divide-y divide-(--border-subtle) rounded-(--radius-md) border border-(--border-subtle) overflow-hidden">
                    {facts.map((f, i) => (
                      <div
                        key={`${f.field}-${i}`}
                        className="flex items-center justify-between gap-3 px-3 py-2.5 bg-(--surface-2) text-xs hover:bg-(--surface-3) transition-colors"
                      >
                        <span className="text-(--text-muted)">{f.label || f.field}</span>
                        <span className="text-(--text-primary) font-mono tabular-nums font-medium">
                          {f.value != null ? String(f.value) : "—"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <NotAdviceBanner />
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

/* ── ScannerResultsTable — stagger rows on mount ── */
export function ScannerResultsTable({
  results,
  onRowClick,
}: {
  results: ScannerResult[];
  onRowClick?: (r: ScannerResult) => void;
}) {
  const [evidenceRow, setEvidenceRow] = React.useState<ScannerResult | null>(null);
  const { reduced } = useMotion();

  if (!results.length) {
    return (
      <EmptyState
        title="No stocks match the current filters"
        description="Adjust the filters or reset to see all results."
      />
    );
  }

  return (
    <>
      <div className="w-full overflow-x-auto rounded-(--radius-lg) border border-(--border-subtle)">
        <table className="w-full border-collapse text-sm" role="grid">
          <thead className="sticky top-0 bg-(--surface-2) z-10">
            <tr>
              {(["Symbol", "Score", "Change", "Signals", "Risk", "Evidence"] as const).map((h) => (
                <th
                  key={h}
                  scope="col"
                  className={cn(
                    "border-b border-(--border-subtle) px-3 py-3 text-[10px] font-semibold text-(--text-muted) uppercase tracking-wider whitespace-nowrap",
                    h === "Score" || h === "Change" || h === "Evidence" ? "text-right" : "text-left"
                  )}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>

          {/* Staggered tbody */}
          <motion.tbody
            variants={staggerContainer(reduced ? 0 : 0.03)}
            initial="hidden"
            animate="visible"
          >
            {results.map((row) => (
              <motion.tr
                key={row.symbol}
                variants={reduced ? undefined : staggerRow}
                className="border-t border-(--border-subtle) hover:bg-(--surface-3) cursor-pointer transition-colors"
                onClick={() => onRowClick?.(row)}
              >
                {/* Symbol */}
                <td className="px-3 py-3">
                  <Link
                    href={`/stocks/${row.symbol}`}
                    className="font-mono font-semibold text-(--text-primary) hover:text-(--accent) transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {row.symbol}
                  </Link>
                  {row.sector && (
                    <p className="text-[10px] text-(--text-muted) mt-0.5">{row.sector}</p>
                  )}
                </td>

                {/* Score */}
                <td className="px-3 py-3 text-right">
                  <ScoreBadge
                    score={row.composite_score}
                    onClick={() => setEvidenceRow(row)}
                  />
                </td>

                {/* Change */}
                <td className="px-3 py-3 text-right">
                  {row.change_pct != null ? (
                    <span className={cn(
                      "inline-flex items-center justify-end gap-0.5 text-xs font-mono tabular-nums font-medium",
                      row.change_pct >= 0 ? "text-(--bullish)" : "text-(--bearish)"
                    )}>
                      {row.change_pct >= 0
                        ? <TrendingUp className="h-3 w-3" aria-hidden />
                        : <TrendingDown className="h-3 w-3" aria-hidden />
                      }
                      {signedPercent(row.change_pct)}
                    </span>
                  ) : (
                    <span className="text-(--text-muted)">—</span>
                  )}
                </td>

                {/* Signals */}
                <td className="px-3 py-3 max-w-[180px]">
                  <ReasonChips reasons={row.reasons.slice(0, 2)} />
                </td>

                {/* Risk */}
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-1">
                    {row.risk_flags.slice(0, 2).map((f) => (
                      <RiskFlagChip key={f} flag={f} />
                    ))}
                  </div>
                </td>

                {/* Evidence */}
                <td className="px-3 py-3 text-right">
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setEvidenceRow(row); }}
                    className={cn(
                      "text-xs text-(--accent) hover:underline",
                      "cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-(--accent) rounded"
                    )}
                    aria-label={`View evidence for ${row.symbol}`}
                  >
                    View
                  </button>
                </td>
              </motion.tr>
            ))}
          </motion.tbody>
        </table>
      </div>

      <EvidenceDrawer
        open={!!evidenceRow}
        onClose={() => setEvidenceRow(null)}
        symbol={evidenceRow?.symbol ?? ""}
        score={evidenceRow?.composite_score}
        reasons={evidenceRow?.reasons}
        riskFlags={evidenceRow?.risk_flags}
        asOf={evidenceRow?.as_of}
      />
    </>
  );
}

/* ── Loading skeleton ── */
export function ScannerSkeleton() {
  return (
    <div className="space-y-2 rounded-(--radius-lg) border border-(--border-subtle) overflow-hidden p-1">
      {[1,2,3,4,5,6].map((i) => (
        <Skeleton key={i} className="h-12 rounded-(--radius-md)" />
      ))}
    </div>
  );
}
