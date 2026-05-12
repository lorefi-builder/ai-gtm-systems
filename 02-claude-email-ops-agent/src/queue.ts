import { z } from 'zod';
import type { DbClient } from './db.js';
import { UnderperformingExperiment, type ProposedSubjectLine } from './schema.js';

/**
 * Returns the losing variant of each active open-rate experiment whose
 * observed open rate is below `threshold` and whose denominator (exposures)
 * is at least `minSampleSize`.
 *
 * "Open rate" is not stored anywhere — it has to be derived from
 * gtm.activities. For each variant we:
 *
 *   - count distinct exposures (the denominator) from gtm.experiment_exposures
 *   - count distinct leads that have an `email_opened` activity occurring at
 *     or after their exposed_at (the numerator)
 *
 * A given lead can be exposed to multiple variants; we link an open back to a
 * variant by requiring the activity's occurred_at to be >= exposed_at on that
 * variant. That's the cleanest temporal join given the current schema, where
 * gtm.activities has no direct FK to gtm.experiment_exposures.
 *
 * We then keep only the non-control variant from each experiment whose
 * primary_metric is 'open_rate', filter by the threshold and sample-size
 * floor, and return one row per experiment.
 */
export async function fetchUnderperformingExperiments(
  client: DbClient,
  threshold: number,
  minSampleSize: number,
): Promise<UnderperformingExperiment[]> {
  const sql = `
    -- Step 1: per-variant exposure counts. One row per (experiment, variant).
    WITH exposures AS (
      SELECT
        v.experiment_id,
        v.id              AS variant_id,
        v.variant_name,
        v.is_control,
        v.subject_line,
        COUNT(*)::int     AS sample_size
      FROM gtm.experiment_variants v
      JOIN gtm.experiment_exposures x ON x.variant_id = v.id
      GROUP BY v.experiment_id, v.id, v.variant_name, v.is_control, v.subject_line
    ),
    -- Step 2: per-variant open counts. A lead is counted once per variant if
    -- they have at least one 'email_opened' activity at or after their
    -- exposure to that variant. COUNT(DISTINCT lead_id) avoids double-counting
    -- leads who open multiple times.
    opens AS (
      SELECT
        x.variant_id,
        COUNT(DISTINCT x.lead_id)::int AS open_count
      FROM gtm.experiment_exposures x
      JOIN gtm.activities a
        ON a.lead_id      = x.lead_id
       AND a.activity_type = 'email_opened'
       AND a.occurred_at  >= x.exposed_at
      GROUP BY x.variant_id
    ),
    -- Step 3: rates. LEFT JOIN opens because a variant with zero opens is
    -- still a valid (and very interesting) row.
    rates AS (
      SELECT
        e.experiment_id,
        e.variant_id,
        e.variant_name,
        e.is_control,
        e.subject_line,
        e.sample_size,
        COALESCE(o.open_count, 0)                                         AS open_count,
        COALESCE(o.open_count, 0)::numeric / NULLIF(e.sample_size, 0)::numeric AS open_rate
      FROM exposures e
      LEFT JOIN opens o ON o.variant_id = e.variant_id
    )
    -- Step 4: pick the losing (non-control) variant of each active open_rate
    -- experiment that is underperforming and powered.
    SELECT
      ex.id            AS experiment_id,
      r.variant_id     AS variant_id,
      ex.name          AS name,
      r.subject_line   AS current_subject,
      r.open_rate      AS current_open_rate,
      r.sample_size    AS sample_size
    FROM rates r
    JOIN gtm.experiments ex ON ex.id = r.experiment_id
    WHERE ex.status         = 'active'
      AND ex.primary_metric = 'open_rate'
      AND r.is_control      = false
      AND r.subject_line   IS NOT NULL
      AND r.sample_size    >= $1::int
      AND r.open_rate       < $2::numeric
    ORDER BY r.open_rate ASC, r.sample_size DESC
  `;

  const result = await client.query<{
    experiment_id: string;
    variant_id: string;
    name: string;
    current_subject: string;
    current_open_rate: string;
    sample_size: number;
  }>(sql, [minSampleSize, threshold]);

  const parsed = z
    .array(UnderperformingExperiment)
    .parse(
      result.rows.map((row) => ({
        experiment_id: row.experiment_id,
        variant_id: row.variant_id,
        name: row.name,
        current_subject: row.current_subject,
        current_open_rate: Number(row.current_open_rate),
        sample_size: row.sample_size,
      })),
    );

  return parsed;
}

export interface WriteAgentOutputArgs {
  agentName: string;
  outputType: 'subject_line_variant' | 'blog_draft' | 'ad_copy' | 'social_caption';
  targetRef: string;
  payload: {
    source_variant_id: string;
    source_subject: string;
    source_open_rate: number;
    source_sample_size: number;
    proposals: ProposedSubjectLine[];
  };
}

/**
 * Inserts a proposal into gtm.agent_outputs. status is intentionally not
 * passed — it defaults to 'pending_review', and the RLS policy on this table
 * would reject any other value when authenticated as gtm_agent anyway. The
 * database is the actual enforcer; this function just respects it.
 */
export async function writeAgentOutput(
  client: DbClient,
  args: WriteAgentOutputArgs,
): Promise<string> {
  const sql = `
    INSERT INTO gtm.agent_outputs (agent_name, output_type, target_ref, payload)
    VALUES ($1, $2, $3, $4::jsonb)
    RETURNING id
  `;

  const result = await client.query<{ id: string }>(sql, [
    args.agentName,
    args.outputType,
    args.targetRef,
    JSON.stringify(args.payload),
  ]);

  const row = result.rows[0];
  if (!row) {
    throw new Error('writeAgentOutput: INSERT returned no row');
  }
  return row.id;
}
