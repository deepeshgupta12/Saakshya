"use client";
import * as React from "react";
import { useStockOverview, useStockTechnicals, useStockAiSummary } from "@/hooks";
import {
  StockHeader, ScannerMembershipChips, KeyStats,
  IndicatorPanel, AiStockSummaryCard, StockSkeleton, NewsPanel,
} from "@/components/stock";
import { PriceChart } from "@/components/charts/PriceChart";
import { ErrorState } from "@/components/ui";

export function StockDetailClient({ symbol }: { symbol: string }) {
  const { data: overview, isLoading, isError, refetch } = useStockOverview(symbol);
  const { data: tech, isLoading: techLoading } = useStockTechnicals(symbol);
  const { data: ai, isLoading: aiLoading, isError: aiError } = useStockAiSummary(symbol);

  if (isLoading) return <StockSkeleton />;
  if (isError || !overview) {
    return <ErrorState message={`No data found for ${symbol}.`} onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <StockHeader
        symbol={overview.symbol}
        sessionDate={overview.session_date}
        close={overview.close}
        scannerMemberships={overview.scanner_memberships}
      />

      {/* Price chart — bars from technicals series (stub: single bar from overview) */}
      <PriceChart
        bars={overview.close != null ? [{
          time:  overview.session_date,
          open:  overview.open  ?? overview.close,
          high:  overview.high  ?? overview.close,
          low:   overview.low   ?? overview.close,
          close: overview.close,
          volume: overview.volume ?? undefined,
        }] : []}
        symbol={symbol}
      />

      {/* Two-column layout: left = indicators/key stats, right = AI + memberships */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <section>
            <h2 className="text-xs font-semibold text-(--text-muted) uppercase tracking-wide mb-3">
              Technical Indicators
            </h2>
            {techLoading ? (
              <div className="h-32 animate-pulse rounded-(--radius-lg) bg-(--surface-3)" />
            ) : tech ? (
              <IndicatorPanel tech={tech} />
            ) : (
              <p className="text-sm text-(--text-muted)">Run the pipeline to compute indicators.</p>
            )}
          </section>

          <section>
            <h2 className="text-xs font-semibold text-(--text-muted) uppercase tracking-wide mb-3">
              Key Stats
            </h2>
            <KeyStats overview={overview} />
          </section>
        </div>

        <div className="space-y-5">
          <ScannerMembershipChips memberships={overview.scanner_memberships} />

          <AiStockSummaryCard
            aiSummary={ai}
            isLoading={aiLoading}
            isError={aiError}
            suppressed={!ai && !aiLoading && !aiError}
          />
        </div>
      </div>

      {/* News & sentiment panel — auth-gated, premium-gated, below-threshold filtered */}
      <NewsPanel symbol={symbol} />
    </div>
  );
}
