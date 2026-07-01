/* Centralized TanStack Query key factory — docs/06 §4. */

export const QK = {
  market: {
    summary: (date?: string) => ["market", "summary", date ?? "latest"] as const,
    breadth: (date?: string) => ["market", "breadth", date ?? "latest"] as const,
  },
  scanners: {
    list: () => ["scanners"] as const,
    results: (
      slug: string,
      filters?: { sector?: string; minScore?: number; limit?: number; offset?: number }
    ) => ["scanner", slug, filters ?? {}] as const,
  },
  stock: {
    overview: (symbol: string, asOf?: string) => ["stock", symbol, "overview", asOf ?? "latest"] as const,
    technicals: (symbol: string, asOf?: string) => ["stock", symbol, "technicals", asOf ?? "latest"] as const,
    aiSummary: (symbol: string, asOf?: string) => ["stock", symbol, "ai-summary", asOf ?? "latest"] as const,
  },
  sectors: {
    list: () => ["sectors"] as const,
    detail: (slug: string) => ["sector", slug] as const,
  },
  ai: {
    marketBrief: (date?: string) => ["ai", "market-brief", date ?? "latest"] as const,
  },
  portfolio: {
    positions:  (id: string, asOf?: string) => ["portfolio", id, "positions",  asOf ?? "latest"] as const,
    overview:   (id: string, asOf?: string) => ["portfolio", id, "overview",   asOf ?? "latest"] as const,
    health:     (id: string, asOf?: string) => ["portfolio", id, "health",     asOf ?? "latest"] as const,
    aiSummary:  (id: string, asOf?: string) => ["portfolio", id, "ai-summary", asOf ?? "latest"] as const,
  },
  strategy: {
    library: ()           => ["strategy", "library"] as const,
    list:    ()           => ["strategy", "list"]    as const,
  },
} as const;
