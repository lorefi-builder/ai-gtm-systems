-- migration_block6.sql
-- =============================================================================
-- Block 6 (Demand Intelligence): per-spec estimated deal value.
--
-- Idempotent. Run in the Supabase SQL editor AFTER schema.sql (Block 1),
-- migration_block3.sql (Block 3), migration_block5a.sql (Block 5A), and
-- migration_block5c.sql (Block 5C).
--
-- Adds to fct_spec:
--   * estimated_value -- estimated deal value captured at DISCOVERY, on EVERY
--                        spec (all statuses), BEFORE the approve/reject decision.
--                        Today dollars live only on fct_opportunity.amount, which
--                        exists for APPROVED specs only — so rejected/escalated
--                        (declined) demand has no $. This column lets declined /
--                        escalated demand be dollar-weighted (e.g. the DI heatmap).
-- =============================================================================

begin;

alter table fct_spec add column if not exists estimated_value numeric(12,2);

comment on column fct_spec.estimated_value is
  'Estimated deal value at discovery, on every spec (all statuses), independent '
  'of fct_opportunity.amount. Enables dollar-weighting of declined/escalated demand.';

commit;

-- NOTE: run this file once, in the Supabase SQL editor, AFTER the prior migrations.
