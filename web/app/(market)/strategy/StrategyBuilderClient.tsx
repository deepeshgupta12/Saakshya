"use client";
/* Strategy / Screener Builder — docs/08 §strategy, docs/19, docs/21 (Mode A).
   Outputs lists of matching stocks, never buy/sell recommendations.
   NL agent output requires explicit user confirmation before any use. */

import * as React from "react";
import { cn } from "@/lib/utils";
import { useStrategyLibrary } from "@/hooks";
import { Skeleton, ErrorState } from "@/components/ui";
import { strategyFromNl, compileScanner } from "@/lib/api/client";
import { Layers, Search, ChevronRight, CheckCircle2, AlertTriangle, Info, Loader2 } from "lucide-react";

/* ── Category badge ── */
const CAT_COLORS: Record<string, string> = {
  momentum:       "bg-violet-400/15 text-violet-300",
  value:          "bg-amber-400/15  text-amber-300",
  "mean-reversion": "bg-sky-400/15  text-sky-300",
  quality:        "bg-emerald-400/15 text-emerald-300",
  technical:      "bg-rose-400/15   text-rose-300",
};

function CategoryBadge({ cat }: { cat: string }) {
  const cls = CAT_COLORS[cat.toLowerCase()] ?? "bg-(--surface-3) text-(--text-muted)";
  return (
    <span className={cn("inline-block rounded-full px-2 py-0.5 text-[10px] font-medium capitalize", cls)}>
      {cat}
    </span>
  );
}

/* ── Library card ── */
type LibraryEntry = {
  library_id: string; name: string; description: string; category: string;
  strategy: Record<string, unknown>;
};

function LibraryCard({ entry, onUse }: { entry: LibraryEntry; onUse: (e: LibraryEntry) => void }) {
  return (
    <div className="rounded-(--radius-lg) border border-(--border-subtle) bg-(--surface-2) p-3 space-y-2 hover:border-(--border-strong) transition-colors">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-(--text-primary) leading-snug">{entry.name}</p>
        <CategoryBadge cat={entry.category} />
      </div>
      <p className="text-xs text-(--text-muted) leading-relaxed">{entry.description}</p>
      <button
        type="button"
        onClick={() => onUse(entry)}
        className={cn(
          "flex items-center gap-1 text-xs font-medium text-(--accent) hover:text-(--accent-strong)",
          "transition-colors duration-(--motion-fast)"
        )}
      >
        Use as screener <ChevronRight className="h-3 w-3" aria-hidden />
      </button>
    </div>
  );
}

/* ── NL result display ── */
interface NlResult {
  strategy: Record<string, unknown> | null;
  validation: { valid: boolean; errors: string[]; warnings: string[] };
  guardrail_passed: boolean;
  requires_confirmation: boolean;
  confirmation_note: string;
  errors: string[];
}

function NlResult({
  result, onConfirm, onDiscard,
}: {
  result: NlResult;
  onConfirm: () => void;
  onDiscard: () => void;
}) {
  const hasErrors = result.errors.length > 0 || !result.validation.valid;
  const strategy  = result.strategy;

  return (
    <div className="space-y-3">
      {/* Guardrail banner */}
      {!result.guardrail_passed && (
        <div className="flex items-start gap-2 rounded-(--radius-md) border border-amber-400/40 bg-amber-400/10 p-3 text-xs text-amber-300">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" aria-hidden />
          <span>The requested output was adjusted to comply with Mode-A: no buy/sell/target/stop-loss levels are emitted.</span>
        </div>
      )}

      {/* Validation errors */}
      {hasErrors && (
        <div className="rounded-(--radius-md) border border-(--bearish)/40 bg-(--bearish)/5 p-3 space-y-1">
          {result.errors.map((e) => (
            <p key={e} className="text-xs text-(--bearish)">{e}</p>
          ))}
          {result.validation.errors.map((e) => (
            <p key={e} className="text-xs text-(--bearish)">{e}</p>
          ))}
        </div>
      )}

      {/* Warnings */}
      {result.validation.warnings.map((w) => (
        <p key={w} className="text-xs text-amber-300">{w}</p>
      ))}

      {/* Strategy preview — read-only JSON tree */}
      {strategy && (
        <div className="rounded-(--radius-md) border border-(--border-subtle) bg-(--surface-3) overflow-auto max-h-64">
          <pre className="p-3 text-[11px] text-(--text-secondary) leading-relaxed">
            {JSON.stringify(strategy, null, 2)}
          </pre>
        </div>
      )}

      {/* Confirmation note */}
      <div className="flex items-start gap-2 rounded-(--radius-md) border border-(--border-subtle) bg-(--surface-2) p-3 text-xs text-(--text-muted)">
        <Info className="h-3.5 w-3.5 shrink-0 mt-0.5 text-(--accent)" aria-hidden />
        <span>{result.confirmation_note || "Review the proposed screener conditions above, then confirm to use."}</span>
      </div>

      {/* CTA */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onConfirm}
          disabled={hasErrors || !strategy}
          className={cn(
            "flex-1 rounded-(--radius-md) px-4 py-2 text-xs font-semibold transition-colors duration-(--motion-fast)",
            hasErrors || !strategy
              ? "bg-(--surface-3) text-(--text-muted) cursor-not-allowed"
              : "bg-(--accent) text-(--text-inverse) hover:bg-(--accent-strong)"
          )}
        >
          <CheckCircle2 className="inline h-3 w-3 mr-1.5" aria-hidden />
          Confirm &amp; use screener
        </button>
        <button
          type="button"
          onClick={onDiscard}
          className="px-4 py-2 text-xs text-(--text-secondary) hover:text-(--text-primary) transition-colors"
        >
          Discard
        </button>
      </div>
    </div>
  );
}

/* ── Main component ── */
export function StrategyBuilderClient() {
  const { data: library, isLoading, isError, refetch } = useStrategyLibrary();

  const [query,      setQuery]      = React.useState("");
  const [nlInput,    setNlInput]    = React.useState("");
  const [nlResult,   setNlResult]   = React.useState<NlResult | null>(null);
  const [nlLoading,  setNlLoading]  = React.useState(false);
  const [nlError,    setNlError]    = React.useState<string | null>(null);
  const [confirmed,  setConfirmed]  = React.useState<Record<string, unknown> | null>(null);
  const [compiling,  setCompiling]  = React.useState(false);
  const [scanRule,   setScanRule]   = React.useState<Record<string, unknown> | null>(null);

  const filtered = React.useMemo(() => {
    if (!library) return [];
    const q = query.toLowerCase();
    return q
      ? library.filter((e) => e.name.toLowerCase().includes(q) || e.category.toLowerCase().includes(q) || e.description.toLowerCase().includes(q))
      : library;
  }, [library, query]);

  async function handleNlSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!nlInput.trim()) return;
    setNlLoading(true); setNlError(null); setNlResult(null); setConfirmed(null); setScanRule(null);
    try {
      const res = await strategyFromNl(nlInput.trim());
      setNlResult(res);
    } catch (err) {
      setNlError(err instanceof Error ? err.message : "Failed to generate screener.");
    } finally {
      setNlLoading(false);
    }
  }

  async function handleConfirm() {
    if (!nlResult?.strategy) return;
    setConfirmed(nlResult.strategy);
    setNlResult(null);
    setCompiling(true);
    try {
      const res = await compileScanner(nlResult.strategy);
      setScanRule(res.scanner_rule);
    } catch {
      /* non-fatal — strategy still saved to confirmed */
    } finally {
      setCompiling(false);
    }
  }

  function handleUseLibraryEntry(entry: LibraryEntry) {
    setConfirmed(entry.strategy);
    setScanRule(null);
    setCompiling(true);
    compileScanner(entry.strategy as Record<string, unknown>)
      .then((res) => setScanRule(res.scanner_rule))
      .catch(() => {/* non-fatal */})
      .finally(() => setCompiling(false));
    setNlResult(null);
    setNlInput("");
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Layers className="h-6 w-6 text-(--accent) shrink-0 mt-0.5" aria-hidden />
        <div>
          <h1 className="text-xl font-bold text-(--text-primary)">Screener Builder</h1>
          <p className="text-xs text-(--text-muted) mt-0.5">
            Build filters that output <strong>lists of matching stocks</strong> — not buy/sell recommendations.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Left: Library browser */}
        <div className="space-y-3">
          <p className="text-xs font-semibold text-(--text-muted) uppercase tracking-wide">Screener Library</p>

          {/* Search bar */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-(--text-muted)" aria-hidden />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by name or category…"
              className={cn(
                "w-full rounded-(--radius-md) border border-(--border-subtle) bg-(--surface-2)",
                "pl-8 pr-3 py-2 text-sm text-(--text-primary) placeholder:text-(--text-muted)",
                "focus:outline-none focus:ring-2 focus:ring-(--accent) focus:border-transparent"
              )}
            />
          </div>

          {isLoading && <Skeleton className="h-48 w-full" />}
          {isError   && <ErrorState message="Unable to load screener library." onRetry={() => refetch()} />}

          {!isLoading && !isError && (
            filtered.length ? (
              <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
                {filtered.map((entry) => (
                  <LibraryCard key={entry.library_id} entry={entry} onUse={handleUseLibraryEntry} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-(--text-muted)">No screeners match your filter.</p>
            )
          )}
        </div>

        {/* Right: NL builder + confirmed result */}
        <div className="space-y-4">
          <p className="text-xs font-semibold text-(--text-muted) uppercase tracking-wide">Natural Language Builder</p>

          <form onSubmit={handleNlSubmit} className="space-y-2">
            <label htmlFor="nl-input" className="text-xs text-(--text-muted)">
              Describe your filter in plain English — e.g. "stocks above 50-DMA with RSI below 40 in large-cap"
            </label>
            <textarea
              id="nl-input"
              value={nlInput}
              onChange={(e) => setNlInput(e.target.value)}
              rows={4}
              placeholder="e.g. momentum stocks with high volume breakout in IT sector…"
              className={cn(
                "w-full rounded-(--radius-md) border border-(--border-subtle) bg-(--surface-2)",
                "px-3 py-2 text-sm text-(--text-primary) placeholder:text-(--text-muted) resize-none",
                "focus:outline-none focus:ring-2 focus:ring-(--accent) focus:border-transparent"
              )}
            />
            <button
              type="submit"
              disabled={nlLoading || !nlInput.trim()}
              className={cn(
                "w-full rounded-(--radius-md) px-4 py-2 text-sm font-semibold transition-colors duration-(--motion-fast)",
                nlLoading || !nlInput.trim()
                  ? "bg-(--surface-3) text-(--text-muted) cursor-not-allowed"
                  : "bg-(--accent) text-(--text-inverse) hover:bg-(--accent-strong)"
              )}
            >
              {nlLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> Generating…
                </span>
              ) : "Generate Screener"}
            </button>
          </form>

          {nlError && (
            <p className="text-xs text-(--bearish) rounded-(--radius-md) border border-(--bearish)/30 bg-(--bearish)/5 px-3 py-2">
              {nlError}
            </p>
          )}

          {nlResult && !confirmed && (
            <NlResult
              result={nlResult}
              onConfirm={handleConfirm}
              onDiscard={() => { setNlResult(null); }}
            />
          )}

          {/* Confirmed screener — compiled rule display */}
          {confirmed && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-(--bullish)">
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                Screener confirmed
              </div>

              {compiling && (
                <div className="flex items-center gap-2 text-xs text-(--text-muted)">
                  <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> Compiling live scanner rule…
                </div>
              )}

              {scanRule && !compiling && (
                <div className="space-y-1">
                  <p className="text-xs text-(--text-muted)">Compiled live scanner rule (entry conditions only):</p>
                  <div className="rounded-(--radius-md) border border-(--border-subtle) bg-(--surface-3) overflow-auto max-h-48">
                    <pre className="p-3 text-[11px] text-(--text-secondary) leading-relaxed">
                      {JSON.stringify(scanRule, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              <button
                type="button"
                onClick={() => { setConfirmed(null); setScanRule(null); }}
                className="text-xs text-(--text-muted) hover:text-(--text-secondary) transition-colors"
              >
                Clear and start over
              </button>
            </div>
          )}

          {/* Mode-A disclosure */}
          <div className="flex items-start gap-2 rounded-(--radius-md) border border-(--border-subtle) bg-(--surface-2) p-3 text-xs text-(--text-muted)">
            <Info className="h-3.5 w-3.5 shrink-0 mt-0.5 text-(--accent)" aria-hidden />
            <span>
              Screeners output <strong>lists of stocks matching the filter</strong>.
              They are analytical tools — not buy recommendations, stock tips or investment advice.
              Stop-loss / target / trailing-stop parameters are backtest-only and are removed from live scanner output.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
