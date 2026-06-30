/* Feature flags — docs/06 §10.
   RA-gated flags are compile-time-safe defaults OFF.
   No client action can enable them — requires a deploy + server config + RA registration. */

export const flags = {
  /** Entry / target / stop-loss overlay — RA-gated, Phase 5. */
  raRecommendationLayer: false,
  /** Per-stock technical level annotations — RA-gated, Phase 5. */
  technicalLevels: false,
  /** News sentiment feed — Phase 2. */
  newsSentiment: false,
  /** Strategy builder — Phase 3. */
  strategyBuilder: false,
  /** Backtesting — Phase 4. */
  backtesting: false,
  /** Thematic baskets — Phase 3. */
  themes: false,
  /** ML probability bands — Phase 5. */
  mlProbabilityBands: false,
} as const;

export type FlagKey = keyof typeof flags;

export function getFlag(key: FlagKey): boolean {
  return flags[key];
}
