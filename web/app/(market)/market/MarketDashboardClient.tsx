"use client";
import { useMarketSummary, useSectors, useMarketBrief } from "@/hooks";
import {
  IndexStrip, BreadthPanel, SectorHeatmap, AiMarketSummaryCard,
  MarketMoversTable, MarketSkeleton, DataConfidenceIndicator,
} from "@/components/market";
import { ErrorState } from "@/components/ui";

export function MarketDashboardClient() {
  const { data: summary, isLoading, isError, refetch } = useMarketSummary();
  const { data: sectors } = useSectors();
  const { data: brief }   = useMarketBrief();

  if (isLoading) return <MarketSkeleton />;
  if (isError || !summary) {
    return <ErrorState message="Unable to load market data." onRetry={() => refetch()} />;
  }

  const briefSuppressed = !brief || !!brief.suppressed || !!brief.degraded;

  return (
    <div className="space-y-6">
      {/* Scanner count strip */}
      <IndexStrip summary={summary} />

      {/* Breadth + AI summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <BreadthPanel summary={summary} />
        </div>
        <AiMarketSummaryCard
          suppressed={briefSuppressed}
          narrative={briefSuppressed ? undefined : brief?.brief}
          dataConfidence={briefSuppressed ? "low" : "high"}
        />
      </div>

      {/* Sector heatmap */}
      {sectors?.length ? (
        <div>
          <h2 className="text-sm font-semibold text-(--text-muted) mb-3 uppercase tracking-wide">
            Sector Strength
          </h2>
          <SectorHeatmap sectors={sectors} />
        </div>
      ) : null}

      {/* Movers placeholder — requires dedicated movers endpoint (Phase 2) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MarketMoversTable title="Top Gainers" movers={[]} emptyText="Movers available after Phase 2" />
        <MarketMoversTable title="Top Losers"  movers={[]} emptyText="Movers available after Phase 2" />
        <MarketMoversTable title="Most Active" movers={[]} emptyText="Movers available after Phase 2" />
      </div>
    </div>
  );
}
