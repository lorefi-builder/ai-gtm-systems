-- migration_block5c.sql
-- =============================================================================
-- Block 5C: opportunity revenue/win-type fields + stage history (for velocity).
--
-- Idempotent. Run in the Supabase SQL editor AFTER schema.sql (Block 1),
-- migration_block3.sql (Block 3), and migration_block5a.sql (Block 5A).
--
-- Adds to fct_opportunity:
--   * win_type -- only meaningful for Closed Won; null otherwise. One of:
--                 new_logo | prior_loss_now_won | renewal | reactivation
--   * acv      -- annual contract value (the revenue figure for the deal)
-- New table modeling Salesforce Opportunity History so stage velocity (days
-- between stages) is computable:
--   fct_opportunity_stage_history(opportunity_id, stage, entered_at, exited_at)
-- =============================================================================

begin;

-- --- fct_opportunity: revenue + win-type columns -----------------------------
alter table fct_opportunity add column if not exists win_type text;
alter table fct_opportunity add column if not exists acv numeric(12,2);

comment on column fct_opportunity.win_type is
  'Only meaningful for Closed Won (null otherwise): '
  'new_logo | prior_loss_now_won | renewal | reactivation.';
comment on column fct_opportunity.acv is
  'Annual contract value (revenue). Distinct from pipeline `amount`.';

-- win_type domain guard (null allowed). Drop + re-add so the file re-runs cleanly.
alter table fct_opportunity drop constraint if exists fct_opportunity_win_type_check;
alter table fct_opportunity add constraint fct_opportunity_win_type_check
  check (win_type is null or win_type in
    ('new_logo', 'prior_loss_now_won', 'renewal', 'reactivation'));

-- --- fct_opportunity_stage_history (SF Opportunity History analog) ------------
create table if not exists fct_opportunity_stage_history (
  history_id     uuid primary key default gen_random_uuid(),
  opportunity_id uuid references fct_opportunity (opportunity_id),
  stage          text,                    -- Discovery|Proposal|Negotiation|Closed Won|Closed Lost
  entered_at     timestamptz,
  exited_at      timestamptz              -- null = still in this stage
);

comment on table fct_opportunity_stage_history is
  'When an opportunity entered/exited each stage. exited_at null = current stage. '
  'Used to compute average stage velocity (days between consecutive stages).';

create index if not exists idx_opp_stage_history_opp on fct_opportunity_stage_history (opportunity_id);
create index if not exists idx_opp_stage_history_stage on fct_opportunity_stage_history (stage);

commit;

-- NOTE: run this file once, in the Supabase SQL editor, AFTER the prior migrations.
