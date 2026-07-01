"use client";
/* Compliance wrappers — mandatory per docs/06 §3, docs/14, SPEC §3, §6.
   Every AI output and RA-gated slot must use these. */

import * as React from "react";
import { Shield, Lock, Info, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

/* ── NotAdviceBanner ── docs/07 §2.11
   Subtle, persistent. aria-live so screen readers catch dynamic injection. */
export function NotAdviceBanner({ className }: { className?: string }) {
  return (
    <div
      role="note"
      aria-live="polite"
      aria-label="Not investment advice"
      className={cn(
        "flex items-start gap-2 rounded-(--radius-sm)",
        "border border-(--warning)/20 bg-(--warning)/5",
        "px-3 py-2 text-xs text-(--text-muted)",
        className
      )}
    >
      <Info className="h-3 w-3 shrink-0 mt-0.5 text-(--warning)" aria-hidden />
      <span className="leading-relaxed">
        Analytics and evidence only — <strong className="text-(--text-secondary) font-medium">not investment advice</strong>.
        All outputs are data-derived descriptions. Verify independently before acting.
      </span>
    </div>
  );
}

/* ── GroundingBadge ── docs/07 §2.7
   Wraps every AI-generated text surface. Never removed or hidden. */
export function GroundingBadge({
  onViewEvidence,
  className,
}: {
  onViewEvidence?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 text-xs text-(--text-muted)",
        "rounded-(--radius-sm) bg-(--ai)/5 border border-(--ai)/15 px-3 py-1.5",
        className
      )}
      role="note"
      aria-label="This AI summary is grounded in the stock's computed signals"
    >
      <Shield className="h-3 w-3 text-(--ai) shrink-0" aria-hidden />
      <span className="leading-snug">
        Grounded in this stock&apos;s signals · not investment advice
      </span>
      {onViewEvidence && (
        <button
          type="button"
          onClick={onViewEvidence}
          className={cn(
            "ml-auto shrink-0 inline-flex items-center gap-1",
            "text-(--accent) hover:text-(--accent-strong) hover:underline",
            "cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-(--accent) rounded",
            "transition-colors"
          )}
          aria-label="View evidence: the data sources behind this AI summary"
        >
          View evidence
          <ExternalLink className="h-2.5 w-2.5" aria-hidden />
        </button>
      )}
    </div>
  );
}

/* ── RaGatedPlaceholder ── docs/07 §2.11
   Occupies every slot where entry/target/SL would go.
   NEVER empty — always explains what it is and why it's locked. */
export function RaGatedPlaceholder({
  label = "Entry / Target / Stop-Loss",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2",
        "rounded-(--radius-lg) border border-dashed border-(--border-strong)",
        "bg-(--surface-2) px-4 py-6 text-center",
        className
      )}
      role="presentation"
      aria-label={`${label} — Available with Research Analyst registration`}
    >
      <div className="flex h-8 w-8 items-center justify-center rounded-(--radius-md) bg-(--surface-3)">
        <Lock className="h-4 w-4 text-(--text-muted) opacity-70" aria-hidden />
      </div>
      <div>
        <p className="text-xs font-medium text-(--text-muted)">{label}</p>
        <p className="text-[11px] text-(--text-muted) opacity-60 mt-1 max-w-55 leading-relaxed">
          Available with Research Analyst registration (SEBI RA)
        </p>
      </div>
    </div>
  );
}
