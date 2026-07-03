"use client";
/* Portfolio screen — docs/08 §portfolio, docs/16, docs/21 (Mode A).
   Evidence-led: all numbers from API, no AI-invented values. */

import { cn } from "@/lib/utils";
import {
  usePortfolioPositions, usePortfolioOverview, usePortfolioHealth, usePortfolioAiSummary,
} from "@/hooks";
import { Skeleton, ErrorState } from "@/components/ui";
import { ShieldAlert, TrendingUp, TrendingDown, Info } from "lucide-react";

interface Props { portfolioId: string }

interface Position {
  symbol: string; exchange: string; quantity: number;
  avg_buy_price: number; invested_value: number;
  current_value: number | null; last_close: number | null;
  unrealized_pnl: number | null; unrealized_pnl_pct: number | null;
  realized_pnl: number; day_change_pct: number | null;
  sector: string | null; market_cap_band: string | null;
  data_confidence: string;
}

/* ── Health gauge: numeric score + band badge ── */
function HealthGauge({ score, band }: { score: number | null; band: string | null }) {
  const pct = score != null ? Math.max(0, Math.min(100, score)) : 0;
  const color =
    pct >= 80 ? "text-(--bullish)"   :
    pct >= 60 ? "text-(--accent)"    :
    pct >= 40 ? "text-amber-400"     :
                "text-(--bearish)";
  const ring =
    pct >= 80 ? "stroke-[var(--bullish)]"   :
    pct >= 60 ? "stroke-[var(--accent)]"    :
    pct >= 40 ? "stroke-amber-400"           :
                "stroke-[var(--bearish)]";

  const r    = 38;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="96" height="96" viewBox="0 0 96 96" aria-label={`Health score ${score ?? "—"}`}>
        <circle cx="48" cy="48" r={r} fill="none" stroke="var(--border-subtle)" strokeWidth="8" />
        <circle
          cx="48" cy="48" r={r} fill="none" strokeWidth="8"
          className={ring}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 48 48)"
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
        <text x="48" y="54" textAnchor="middle" className="fill-[var(--text-primary)] text-xl font-bold" style={{ fontSize: 18 }}>
          {score != null ? Math.round(score) : "—"}
        </text>
      </svg>
      {band && (
        <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full", color, "bg-(--surface-3)")}>
          {band}
        </span>
      )}
    </div>
  );
}

/* ── Currency formatter ── */
const inr = (v: number | null | undefined) =>
  v != null ? `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}` : "—";
const pct = (v: number | null | undefined) =>
  v != null ? `${v >= 0 ? "+" : ""}${v.toFixed(2)}%` : "—";

/* ── Holdings row ── */
function HoldingRow({ pos }: { pos: Position }) {
  const pnlPos = (pos.unrealized_pnl ?? 0) >= 0;
  return (
    <tr className="border-t border-(--border-subtle) hover:bg-(--surface-2) transition-colors">
      <td className="px-3 py-3 font-medium text-(--text-primary) text-sm">{pos.symbol}</td>
      <td className="px-3 py-3 text-right text-xs text-(--text-secondary) tabular-nums">{pos.quantity}</td>
      <td className="px-3 py-3 text-right text-xs text-(--text-secondary) tabular-nums">{inr(pos.avg_buy_price)}</td>
      <td className="px-3 py-3 text-right text-xs text-(--text-secondary) tabular-nums">{inr(pos.last_close)}</td>
      <td className="px-3 py-3 text-right text-xs font-medium tabular-nums">{inr(pos.current_value)}</td>
      <td className={cn("px-3 py-3 text-right text-xs font-medium tabular-nums", pnlPos ? "text-(--bullish)" : "text-(--bearish)")}>
        {inr(pos.unrealized_pnl)}
      </td>
      <td className={cn("px-3 py-3 text-right text-xs font-medium tabular-nums", pnlPos ? "text-(--bullish)" : "text-(--bearish)")}>
        {pct(pos.unrealized_pnl_pct)}
      </td>
      <td className="px-3 py-3 text-right text-xs text-(--text-muted)">
        {pos.sector ?? "—"}
      </td>
    </tr>
  );
}

/* ── Sector allocation mini-bars ── */
function SectorBars({ items }: { items: Array<{ sector: string; weight_pct: number | null }> }) {
  if (!items.length) return <p className="text-xs text-(--text-muted)">No sector data.</p>;
  return (
    <div className="space-y-2">
      {items.slice(0, 8).map((s) => (
        <div key={s.sector} className="flex items-center gap-2">
          <span className="w-28 shrink-0 text-xs text-(--text-secondary) truncate">{s.sector}</span>
          <div className="flex-1 h-1.5 rounded-full bg-(--surface-3) overflow-hidden">
            <div
              className="h-full rounded-full bg-(--accent) transition-all duration-500"
              style={{ width: `${Math.max(2, s.weight_pct ?? 0)}%` }}
            />
          </div>
          <span className="w-10 text-right text-xs text-(--text-muted) tabular-nums">
            {s.weight_pct != null ? `${s.weight_pct.toFixed(1)}%` : "—"}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ── AI Summary card ── */
function AiSummaryCard({ summary, suppressed, degraded }: { summary?: string; suppressed?: boolean; degraded?: boolean }) {
  if (suppressed || !summary) {
    return (
      <div className="rounded-(--radius-lg) border border-(--border-subtle) bg-(--surface-2) p-4">
        <p className="text-xs text-(--text-muted)">AI summary not available for this portfolio.</p>
      </div>
    );
  }
  return (
    <div className={cn("rounded-(--radius-lg) border p-4 space-y-2", degraded ? "border-amber-400/40 bg-amber-400/5" : "border-(--border-subtle) bg-(--surface-2)")}>
      <div className="flex items-center gap-1.5 text-xs text-(--text-muted)">
        <Info className="h-3 w-3 shrink-0" aria-hidden />
        AI Portfolio Observations
        {degraded && <span className="ml-auto text-amber-400">Degraded</span>}
      </div>
      <p className="text-sm text-(--text-primary) leading-relaxed whitespace-pre-line">{summary}</p>
      <p className="text-[10px] text-(--text-muted) border-t border-(--border-subtle) pt-2 mt-2">
        These are observations, not recommendations. Not investment advice.
      </p>
    </div>
  );
}

/* ── Main component ── */
export function PortfolioClient({ portfolioId }: Props) {
  const {
    data: positions, isLoading: posLoad, isError: posErr, refetch: posRefetch,
  } = usePortfolioPositions(portfolioId);
  const { data: overview, isLoading: ovLoad } = usePortfolioOverview(portfolioId);
  const { data: health,   isLoading: hLoad  } = usePortfolioHealth(portfolioId);
  const { data: aiData,   isLoading: aiLoad } = usePortfolioAiSummary(portfolioId);

  const loading = posLoad || ovLoad || hLoad;

  if (loading) return <Skeleton className="h-96 w-full" />;
  if (posErr)  return <ErrorState message="Unable to load portfolio." onRetry={() => posRefetch()} />;

  const agg = (overview?.aggregate ?? {}) as Record<string, number | null>;
  const totalValue    = agg.total_value as number | null;
  const totalInvested = agg.total_invested as number | null;
  const unrealizedPnl = agg.total_unrealized_pnl as number | null;
  const realizedPnl   = agg.total_realized_pnl as number | null;
  const overallPnlPct = totalInvested && totalInvested > 0 && unrealizedPnl != null
    ? (unrealizedPnl / totalInvested) * 100 : null;
  const pnlPositive   = (unrealizedPnl ?? 0) >= 0;

  const sectorItems = (overview?.sector_allocation ?? []) as Array<{ sector: string; weight_pct: number | null }>;
  const healthScore = health?.portfolio_health_score ?? null;
  const healthBand  = health?.band ?? null;
  const drivers     = health?.drivers ?? [];

  const hasPositions = positions && positions.length > 0;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-(--text-primary)">Portfolio</h1>
          <p className="text-xs text-(--text-muted) mt-0.5">Holdings, P&amp;L and risk — evidence only. Not investment advice.</p>
        </div>
        <ShieldAlert className="h-5 w-5 text-(--text-muted) shrink-0" aria-hidden />
      </div>

      {!hasPositions ? (
        <div className="rounded-(--radius-lg) border border-(--border-subtle) bg-(--surface-2) p-8 text-center">
          <p className="text-sm text-(--text-secondary) mb-1">No holdings recorded yet.</p>
          <p className="text-xs text-(--text-muted)">Add transactions via the API to populate your portfolio.</p>
        </div>
      ) : (
        <>
          {/* Summary bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Current Value",    value: inr(totalValue) },
              { label: "Invested",         value: inr(totalInvested) },
              {
                label: "Unrealised P&L",
                value: `${inr(unrealizedPnl)} (${pct(overallPnlPct)})`,
                color: pnlPositive ? "text-(--bullish)" : "text-(--bearish)",
              },
              { label: "Realised P&L",     value: inr(realizedPnl) },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-(--radius-lg) border border-(--border-subtle) bg-(--surface-2) p-3">
                <p className="text-[10px] text-(--text-muted) uppercase tracking-wide mb-1">{label}</p>
                <p className={cn("text-sm font-semibold tabular-nums text-(--text-primary)", color)}>{value}</p>
              </div>
            ))}
          </div>

          {/* Health + sector allocation side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Health gauge */}
            <div className="rounded-(--radius-lg) border border-(--border-subtle) bg-(--surface-2) p-4 flex flex-col items-center gap-3">
              <p className="text-xs font-semibold text-(--text-muted) uppercase tracking-wide">Portfolio Health</p>
              {hLoad ? <Skeleton className="h-24 w-24 rounded-full" /> : (
                <HealthGauge score={healthScore} band={healthBand} />
              )}
              {drivers.length > 0 && (
                <ul className="w-full space-y-1">
                  {drivers.slice(0, 4).map((d) => (
                    <li key={d} className="flex items-start gap-1.5 text-xs text-(--text-secondary)">
                      <span className="mt-0.5 h-1 w-1 shrink-0 rounded-full bg-(--text-muted)" />
                      {d}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Sector allocation */}
            <div className="lg:col-span-2 rounded-(--radius-lg) border border-(--border-subtle) bg-(--surface-2) p-4 space-y-3">
              <p className="text-xs font-semibold text-(--text-muted) uppercase tracking-wide">Sector Allocation</p>
              <SectorBars items={sectorItems} />
            </div>
          </div>

          {/* AI summary */}
          {!aiLoad && (
            <AiSummaryCard
              summary={aiData?.summary}
              suppressed={aiData?.suppressed}
              degraded={aiData?.degraded}
            />
          )}

          {/* Holdings table */}
          <div>
            <h2 className="text-sm font-semibold text-(--text-muted) mb-3 uppercase tracking-wide">Holdings</h2>
            <div className="rounded-(--radius-lg) border border-(--border-subtle) overflow-x-auto">
              <table className="w-full border-collapse text-sm min-w-[700px]">
                <thead className="bg-(--surface-2)">
                  <tr>
                    {["Symbol", "Qty", "Avg Price", "Last Close", "Value", "Unrealised P&L", "%", "Sector"].map((h) => (
                      <th
                        key={h}
                        className={cn("px-3 py-3 text-xs text-(--text-muted)", h === "Symbol" ? "text-left" : "text-right")}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos) => (
                    <HoldingRow key={`${pos.symbol}-${pos.exchange}`} pos={pos} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Risk drivers */}
          {(health?.components ?? []).length > 0 && (
            <div className="rounded-(--radius-lg) border border-(--border-subtle) bg-(--surface-2) p-4 space-y-2">
              <p className="text-xs font-semibold text-(--text-muted) uppercase tracking-wide">Risk Components</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {(health!.components as Array<Record<string, unknown>>).map((c, i) => {
                  const name  = (c.component ?? c.name ?? `Component ${i + 1}`) as string;
                  const score = c.score != null ? Number(c.score) : null;
                  return (
                    <div key={name} className="flex items-center justify-between text-xs text-(--text-secondary) px-2 py-1.5 rounded bg-(--surface-3)">
                      <span className="truncate capitalize">{String(name).replace(/_/g, " ")}</span>
                      <span className={cn("tabular-nums font-medium ml-2 shrink-0", score != null && score > 50 ? "text-(--bearish)" : "text-(--bullish)")}>
                        {score != null ? Math.round(score) : "—"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Evidence affordance */}
          <p className="text-[10px] text-(--text-muted) border-t border-(--border-subtle) pt-3">
            Data source: T+1 EOD prices. Health score is a composite of concentration, sector balance, volatility,
            technical, news and cap-exposure signals — not a prediction. Not investment advice.
          </p>
        </>
      )}
    </div>
  );
}
