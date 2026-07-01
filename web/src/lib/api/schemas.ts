/* Zod schemas for API responses — kept in sync with docs/10 and backend envelope.
   Invalid shapes throw; never render unvalidated data. */

import { z } from "zod";

/* ── Shared envelope parts ── */
const metaSchema = z.object({
  as_of:            z.string().nullable().optional(),
  data_confidence:  z.string().optional(),
  source:           z.string().optional(),
  is_adjusted:      z.boolean().optional(),
  request_id:       z.string().optional(),
  cache:            z.string().nullable().optional(),
  page: z.object({
    limit:  z.number(),
    offset: z.number(),
    total:  z.number(),
  }).nullable().optional(),
});

function envelope<T extends z.ZodTypeAny>(dataSchema: T) {
  return z.object({ data: dataSchema, meta: metaSchema, error: z.null() });
}

/* ── Error envelope ── */
const errorEnvelope = z.object({
  data:  z.null(),
  meta:  z.object({ request_id: z.string().optional() }),
  error: z.object({
    code:      z.string(),
    message:   z.string(),
    details:   z.record(z.string(), z.unknown()).optional(),
    retriable: z.boolean().optional(),
  }),
});

/* ── Market ── */
const marketSummarySchema = z.object({
  scanner_counts: z.record(
    z.string(),
    z.object({ count: z.number(), label: z.string().optional() })
  ),
  total_members:  z.number(),
  advance_count:  z.number().optional(),
  decline_count:  z.number().optional(),
  as_of:          z.string().optional(),
});

/* ── Scanner ── */
const scannerMetaSchema = z.object({
  scanner:         z.string(),
  label:           z.string(),
  description:     z.string().optional(),
  result_count:    z.number().optional(),
  last_run_at:     z.string().optional(),
  validation_note: z.string().optional(),
});

const scannerResultSchema = z.object({
  rank:             z.number().optional(),
  symbol:           z.string(),
  name:             z.string().optional(),
  sector:           z.string().optional(),
  composite_score:  z.number(),
  sub_scores:       z.record(z.string(), z.unknown()).optional(),
  reasons:          z.array(z.string()).optional(),
  signal_tags:      z.array(z.string()).optional(),
  risk_flags:       z.array(z.string()).optional(),
  data_confidence:  z.string().optional(),
  last_close:       z.number().nullable().optional(),
  change_pct:       z.number().nullable().optional(),
  volume:           z.number().nullable().optional(),
  as_of:            z.string().optional(),
});

/* ── Stock ── */
const stockOverviewSchema = z.object({
  symbol:              z.string(),
  session_date:        z.string(),
  open:                z.number().nullable().optional(),
  high:                z.number().nullable().optional(),
  low:                 z.number().nullable().optional(),
  close:               z.number().nullable().optional(),
  volume:              z.number().nullable().optional(),
  delivery_pct:        z.number().nullable().optional(),
  scanner_memberships: z.array(z.string()).optional(),
  disclaimer:          z.string().optional(),
});

const stockTechnicalsSchema = z.record(z.string(), z.unknown());

const citedFactSchema = z.object({
  field: z.string(),
  value: z.unknown(),
  label: z.string().optional(),
});

const aiSummarySchema = z.object({
  symbol:        z.string(),
  session_date:  z.string(),
  summary:       z.string(),
  cited_facts:   z.array(citedFactSchema).optional(),
  risk_notes:    z.array(z.string()).optional(),
  model_version: z.string().optional(),
  disclaimer:    z.string().optional(),
});

/* ── Sectors ── */
const sectorSummarySchema = z.object({
  sector_id:      z.string(),
  name:           z.string(),
  slug:           z.string(),
  strength_score: z.number().nullable().optional(),
  change_pct:     z.number().nullable().optional(),
  breadth:        z.number().nullable().optional(),
  rank:           z.number().nullable().optional(),
  narrative:      z.string().nullable().optional(),
  constituents: z.array(z.object({
    symbol:       z.string(),
    name:         z.string().optional(),
    change_pct:   z.number().nullable().optional(),
    volume_ratio: z.number().nullable().optional(),
  })).optional(),
});

/* ── AI market brief ── */
const marketBriefSchema = z.object({
  brief:         z.string(),
  session_date:  z.string().nullable().optional(),
  model_version: z.string().nullable().optional(),
  cached:        z.boolean().optional(),
  suppressed:    z.boolean().optional(),
  degraded:      z.boolean().optional(),
});

export const schemas = {
  errorEnvelope,
  marketBriefEnvelope:      envelope(marketBriefSchema),
  marketSummaryEnvelope:    envelope(marketSummarySchema),
  scannerListEnvelope:      envelope(z.array(scannerMetaSchema)),
  scannerResultsEnvelope:   envelope(z.array(scannerResultSchema)),
  stockOverviewEnvelope:    envelope(stockOverviewSchema),
  stockTechnicalsEnvelope:  envelope(stockTechnicalsSchema),
  aiSummaryEnvelope:        envelope(aiSummarySchema),
  sectorListEnvelope:       envelope(z.array(sectorSummarySchema)),
  sectorDetailEnvelope:     envelope(sectorSummarySchema),
} as const;
