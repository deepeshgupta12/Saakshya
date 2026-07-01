/* Typed API client — docs/06 §5, docs/10.
   All data flows through typed functions + Zod validation.
   Invalid response shapes throw (surface as ErrorState), never render. */

import { z } from "zod";
import type {
  MarketSummary, ScannerMeta, ScannerResult, StockOverview,
  StockTechnicals, AiSummary, SectorSummary,
} from "@/types";
import { schemas } from "./schemas";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    next: { revalidate: 0 },
  });

  const raw: unknown = await res.json();

  if (!res.ok) {
    const errEnv = schemas.errorEnvelope.safeParse(raw);
    const msg = errEnv.success ? errEnv.data.error.message : `API ${res.status}`;
    throw new Error(msg);
  }

  const parsed = schema.safeParse(raw);
  if (!parsed.success) {
    throw new Error(`Response shape invalid: ${parsed.error.message}`);
  }
  return parsed.data;
}

/* ── Market ── */
export async function fetchMarketSummary(asOf?: string): Promise<MarketSummary> {
  const qs = asOf ? `?as_of=${asOf}` : "";
  const env = await apiFetch(`/v1/market/summary${qs}`, schemas.marketSummaryEnvelope);
  return {
    scanner_counts: env.data.scanner_counts as MarketSummary["scanner_counts"],
    total_members:  env.data.total_members,
    advance_count:  env.data.advance_count ?? 0,
    decline_count:  env.data.decline_count ?? 0,
    as_of:          env.data.as_of,
  };
}

/* ── Scanners ── */
export async function fetchScannerList(): Promise<ScannerMeta[]> {
  const env = await apiFetch("/v1/scanners", schemas.scannerListEnvelope);
  return env.data.map((s) => ({
    scanner:         s.scanner,
    label:           s.label,
    description:     s.description ?? "",
    result_count:    s.result_count ?? 0,
    last_run_at:     s.last_run_at ?? "",
    validation_note: s.validation_note,
  }));
}

export async function fetchScannerResults(
  slug: string,
  params?: { minScore?: number; limit?: number; offset?: number; sector?: string }
): Promise<{ results: ScannerResult[]; total: number; asOf: string }> {
  const sp = new URLSearchParams();
  if (params?.minScore) sp.set("min_score", String(params.minScore));
  if (params?.limit)    sp.set("limit",     String(params.limit));
  if (params?.offset)   sp.set("offset",    String(params.offset));
  if (params?.sector)   sp.set("sector",    params.sector);
  const qs = sp.toString() ? `?${sp}` : "";
  // URL slugs use hyphens (moving-average) but backend keys use underscores (moving_average)
  const apiSlug = slug.replace(/-/g, "_");
  const env = await apiFetch(`/v1/scanners/${apiSlug}${qs}`, schemas.scannerResultsEnvelope);
  const results: ScannerResult[] = env.data.map((r) => ({
    rank:             r.rank ?? 0,
    symbol:           r.symbol,
    name:             r.name ?? "",
    sector:           r.sector,
    composite_score:  r.composite_score,
    sub_scores:       r.sub_scores ?? {},
    reasons:          r.reasons ?? [],
    signal_tags:      r.signal_tags ?? [],
    risk_flags:       r.risk_flags ?? [],
    data_confidence:  (r.data_confidence as ScannerResult["data_confidence"]) ?? "MEDIUM",
    last_close:       r.last_close,
    change_pct:       r.change_pct,
    volume:           r.volume,
    as_of:            r.as_of ?? "",
  }));
  return {
    results,
    total: env.meta.page?.total ?? results.length,
    asOf:  env.meta.as_of ?? "",
  };
}

/* ── Stocks ── */
export async function fetchStockOverview(symbol: string, asOf?: string): Promise<StockOverview> {
  const qs = asOf ? `?as_of=${asOf}` : "";
  const env = await apiFetch(`/v1/stocks/${symbol}/overview${qs}`, schemas.stockOverviewEnvelope);
  return {
    symbol:              env.data.symbol,
    session_date:        env.data.session_date,
    open:                env.data.open,
    high:                env.data.high,
    low:                 env.data.low,
    close:               env.data.close,
    volume:              env.data.volume,
    delivery_pct:        env.data.delivery_pct,
    scanner_memberships: env.data.scanner_memberships ?? [],
    disclaimer:          env.data.disclaimer ?? "",
  };
}

export async function fetchStockTechnicals(symbol: string, asOf?: string): Promise<StockTechnicals> {
  const qs = asOf ? `?as_of=${asOf}` : "";
  const env = await apiFetch(`/v1/stocks/${symbol}/technicals${qs}`, schemas.stockTechnicalsEnvelope);
  return env.data as StockTechnicals;
}

export async function fetchStockAiSummary(symbol: string, asOf?: string): Promise<AiSummary> {
  const qs = asOf ? `?as_of=${asOf}` : "";
  const env = await apiFetch(`/v1/stocks/${symbol}/ai-summary${qs}`, schemas.aiSummaryEnvelope);
  return {
    symbol:        env.data.symbol,
    session_date:  env.data.session_date,
    summary:       env.data.summary,
    cited_facts:   (env.data.cited_facts ?? []) as AiSummary["cited_facts"],
    risk_notes:    env.data.risk_notes ?? [],
    model_version: env.data.model_version ?? "",
    disclaimer:    env.data.disclaimer ?? "",
  };
}

/* ── AI ── */
export async function fetchMarketBrief(asOf?: string): Promise<{
  brief: string; session_date?: string | null; model_version?: string | null;
  cached?: boolean; suppressed?: boolean; degraded?: boolean;
}> {
  const qs = asOf ? `?date=${asOf}` : "";
  const env = await apiFetch(`/api/ai/market-brief${qs}`, schemas.marketBriefEnvelope);
  return env.data;
}

/* ── Sectors ── */
export async function fetchSectors(): Promise<SectorSummary[]> {
  const env = await apiFetch("/v1/sectors", schemas.sectorListEnvelope);
  return env.data.map(toSectorSummary);
}

export async function fetchSectorDetail(slug: string): Promise<SectorSummary> {
  const env = await apiFetch(`/v1/sectors/${slug}`, schemas.sectorDetailEnvelope);
  return toSectorSummary(env.data);
}

function toSectorSummary(s: {
  sector_id: string; name: string; slug: string;
  strength_score?: number | null; change_pct?: number | null;
  breadth?: number | null; rank?: number | null; narrative?: string | null;
  constituents?: Array<{ symbol: string; name?: string; change_pct?: number | null; volume_ratio?: number | null }>;
}): SectorSummary {
  return {
    sector_id:      s.sector_id,
    name:           s.name,
    slug:           s.slug,
    strength_score: s.strength_score,
    change_pct:     s.change_pct,
    breadth:        s.breadth,
    rank:           s.rank,
    narrative:      s.narrative,
    constituents:   s.constituents ?? [],
  };
}
