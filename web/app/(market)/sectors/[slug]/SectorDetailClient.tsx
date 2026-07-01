"use client";
import Link from "next/link";
import { useSector } from "@/hooks";
import { Skeleton, ErrorState, Badge } from "@/components/ui";
import { cn } from "@/lib/utils";

export function SectorDetailClient({ slug }: { slug: string }) {
  const { data, isLoading, isError, refetch } = useSector(slug);

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (isError || !data) return <ErrorState message={`Sector "${slug}" not found.`} onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      {/* Sector header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-(--text-primary)">{data.name}</h1>
          {data.narrative && (
            <p className="text-sm text-(--text-secondary) mt-1 max-w-xl">{data.narrative}</p>
          )}
        </div>
        <div className="text-right">
          {data.change_pct != null && (
            <p className={cn("text-lg font-semibold tabular-nums", data.change_pct >= 0 ? "text-(--bullish)" : "text-(--bearish)")}>
              {data.change_pct >= 0 ? "+" : ""}{data.change_pct.toFixed(2)}%
            </p>
          )}
          {data.strength_score != null && (
            <p className="text-xs text-(--text-muted)">Strength score: {Math.round(data.strength_score)}</p>
          )}
        </div>
      </div>

      {/* Constituents */}
      {data.constituents?.length ? (
        <div>
          <h2 className="text-sm font-semibold text-(--text-muted) uppercase tracking-wide mb-3">
            Constituents ({data.constituents.length})
          </h2>
          <div className="rounded-(--radius-lg) border border-(--border-subtle) overflow-hidden">
            <table className="w-full border-collapse text-sm">
              <thead className="bg-(--surface-2)">
                <tr>
                  <th className="px-3 py-3 text-left text-xs text-(--text-muted)">Symbol</th>
                  <th className="px-3 py-3 text-right text-xs text-(--text-muted)">Change %</th>
                  <th className="px-3 py-3 text-right text-xs text-(--text-muted)">Vol Ratio</th>
                </tr>
              </thead>
              <tbody>
                {data.constituents.map((c) => (
                  <tr key={c.symbol} className="border-t border-(--border-subtle) hover:bg-(--surface-3) transition-colors">
                    <td className="px-3 py-3">
                      <Link href={`/stocks/${c.symbol}`} className="font-medium text-(--text-primary) hover:text-(--accent)">
                        {c.symbol}
                      </Link>
                      {c.name && <p className="text-[10px] text-(--text-muted)">{c.name}</p>}
                    </td>
                    <td className={cn("px-3 py-3 text-right tabular-nums text-xs font-medium", (c.change_pct ?? 0) >= 0 ? "text-(--bullish)" : "text-(--bearish)")}>
                      {c.change_pct != null ? `${c.change_pct >= 0 ? "+" : ""}${c.change_pct.toFixed(2)}%` : "—"}
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums text-xs text-(--text-secondary)">
                      {c.volume_ratio != null ? c.volume_ratio.toFixed(2) + "×" : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <p className="text-sm text-(--text-muted)">Constituent data not available for this sector.</p>
      )}
    </div>
  );
}
