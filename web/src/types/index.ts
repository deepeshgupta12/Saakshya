/* Shared TypeScript types — mirrors docs/10 API envelope and domain types. */

export type DataConfidence = "HIGH" | "MEDIUM" | "LOW";

export interface ApiMeta {
  as_of: string | null;
  data_confidence: DataConfidence;
  source: string;
  is_adjusted?: boolean;
  request_id: string;
  cache?: "hit" | "miss" | null;
  page?: {
    limit: number;
    offset: number;
    total: number;
  } | null;
}

export interface ApiEnvelope<T> {
  data: T;
  meta: ApiMeta;
  error: null;
}

export interface ApiError {
  data: null;
  meta: { request_id: string };
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    retriable?: boolean;
  };
}

export type ApiResponse<T> = ApiEnvelope<T> | ApiError;

/* Scanner */
export interface ScannerMeta {
  scanner: string;
  label: string;
  description: string;
  result_count: number;
  last_run_at: string;
  validation_note?: string;
}

export interface ScannerResult {
  rank: number;
  symbol: string;
  name: string;
  sector?: string;
  composite_score: number;
  sub_scores: Record<string, unknown>;
  reasons: string[];
  signal_tags: string[];
  risk_flags: string[];
  data_confidence: DataConfidence;
  last_close?: number | null;
  change_pct?: number | null;
  volume?: number | null;
  as_of: string;
}

/* Stock */
export interface StockOverview {
  symbol: string;
  session_date: string;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  close?: number | null;
  volume?: number | null;
  delivery_pct?: number | null;
  scanner_memberships: string[];
  disclaimer: string;
}

export interface StockTechnicals {
  symbol?: string;
  rsi_14?: number | null;
  macd?: number | null;
  macd_signal?: number | null;
  macd_histogram?: number | null;
  bb_upper?: number | null;
  bb_middle?: number | null;
  bb_lower?: number | null;
  atr_14?: number | null;
  sma_20?: number | null;
  sma_50?: number | null;
  sma_200?: number | null;
  ema_20?: number | null;
  volume_ratio_20d?: number | null;
  delivery_pct?: number | null;
  [key: string]: unknown;
}

export interface AiSummary {
  symbol: string;
  session_date: string;
  summary: string;
  cited_facts: Array<{ field: string; value: unknown; label?: string }>;
  risk_notes: string[];
  model_version: string;
  disclaimer: string;
}

/* Market */
export interface MarketSummary {
  scanner_counts: Record<string, { count: number; label?: string }>;
  total_members: number;
  advance_count: number;
  decline_count: number;
  as_of?: string;
}

/* Sector */
export interface SectorSummary {
  sector_id: string;
  name: string;
  slug: string;
  strength_score?: number | null;
  change_pct?: number | null;
  breadth?: number | null;
  rank?: number | null;
  narrative?: string | null;
  constituents?: Array<{
    symbol: string;
    name?: string;
    change_pct?: number | null;
    volume_ratio?: number | null;
  }>;
}
