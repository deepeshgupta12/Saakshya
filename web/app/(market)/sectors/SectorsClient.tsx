"use client";
import { useSectors } from "@/hooks";
import { SectorHeatmap } from "@/components/market";
import { Skeleton, ErrorState, DataTable } from "@/components/ui";
import Link from "next/link";
import { cn } from "@/lib/utils";
import type { SectorSummary } from "@/types";

export function SectorsClient() {
  const { data, isLoading, isError, refetch } = useSectors();

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (isError || !data) return <ErrorState message="Unable to load sectors." onRetry={() => refetch()} />;
  if (!data.length)    return <p className="text-sm text-[--text-muted]">Sector data not yet available. Run the pipeline.</p>;

  return (
    <div className="space-y-6">
      <SectorHeatmap sectors={data} />

      <div>
        <h2 className="text-sm font-semibold text-[--text-muted] mb-3 uppercase tracking-wide">Sector Rankings</h2>
        <div className="rounded-[--radius-lg] border border-[--border-subtle] overflow-hidden">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-[--surface-2]">
              <tr>
                <th className="px-3 py-3 text-left text-xs text-[--text-muted]">Sector</th>
                <th className="px-3 py-3 text-right text-xs text-[--text-muted]">Change %</th>
                <th className="px-3 py-3 text-right text-xs text-[--text-muted]">Score</th>
                <th className="px-3 py-3 text-right text-xs text-[--text-muted]">Breadth</th>
              </tr>
            </thead>
            <tbody>
              {data.map((sec) => (
                <tr key={sec.sector_id} className="border-t border-[--border-subtle] hover:bg-[--surface-3] transition-colors">
                  <td className="px-3 py-3">
                    <Link href={`/sectors/${sec.slug}`} className="font-medium text-[--text-primary] hover:text-[--accent]">
                      {sec.name}
                    </Link>
                  </td>
                  <td className={cn("px-3 py-3 text-right tabular-nums text-xs font-medium", (sec.change_pct ?? 0) >= 0 ? "text-[--bullish]" : "text-[--bearish]")}>
                    {sec.change_pct != null ? `${sec.change_pct >= 0 ? "+" : ""}${sec.change_pct.toFixed(2)}%` : "—"}
                  </td>
                  <td className="px-3 py-3 text-right tabular-nums text-xs text-[--text-secondary]">
                    {sec.strength_score != null ? Math.round(sec.strength_score) : "—"}
                  </td>
                  <td className="px-3 py-3 text-right tabular-nums text-xs text-[--text-secondary]">
                    {sec.breadth != null ? `${(sec.breadth * 100).toFixed(0)}%` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
