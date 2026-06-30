"use client";
/* All TanStack Query hooks — docs/06 §4.
   These are the ONLY way to fetch server data in components. */

import { useQuery } from "@tanstack/react-query";
import { QK } from "@/constants/query-keys";
import {
  fetchMarketSummary, fetchScannerList, fetchScannerResults,
  fetchStockOverview, fetchStockTechnicals, fetchStockAiSummary,
  fetchSectors, fetchSectorDetail,
} from "@/lib/api/client";

/* Market */
export function useMarketSummary(asOf?: string) {
  return useQuery({
    queryKey: QK.market.summary(asOf),
    queryFn: () => fetchMarketSummary(asOf),
  });
}

/* Scanners */
export function useScannerList() {
  return useQuery({
    queryKey: QK.scanners.list(),
    queryFn: fetchScannerList,
  });
}

export function useScanner(
  slug: string,
  filters?: { sector?: string; minScore?: number; limit?: number; offset?: number }
) {
  return useQuery({
    queryKey: QK.scanners.results(slug, filters),
    queryFn: () => fetchScannerResults(slug, filters),
    enabled: !!slug,
  });
}

/* Stock */
export function useStockOverview(symbol: string, asOf?: string) {
  return useQuery({
    queryKey: QK.stock.overview(symbol, asOf),
    queryFn: () => fetchStockOverview(symbol, asOf),
    enabled: !!symbol,
  });
}

export function useStockTechnicals(symbol: string, asOf?: string) {
  return useQuery({
    queryKey: QK.stock.technicals(symbol, asOf),
    queryFn: () => fetchStockTechnicals(symbol, asOf),
    enabled: !!symbol,
  });
}

export function useStockAiSummary(symbol: string, asOf?: string) {
  return useQuery({
    queryKey: QK.stock.aiSummary(symbol, asOf),
    queryFn: () => fetchStockAiSummary(symbol, asOf),
    enabled: !!symbol,
    /* AI summaries have shorter stale time — re-check after 1h */
    staleTime: 60 * 60 * 1000,
    retry: 1,
  });
}

/* Sectors */
export function useSectors() {
  return useQuery({
    queryKey: QK.sectors.list(),
    queryFn: fetchSectors,
  });
}

export function useSector(slug: string) {
  return useQuery({
    queryKey: QK.sectors.detail(slug),
    queryFn: () => fetchSectorDetail(slug),
    enabled: !!slug,
  });
}
