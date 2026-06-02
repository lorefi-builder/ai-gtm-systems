-- migration_block3.sql
-- =============================================================================
-- Block 3 additions for the Project Assessment Agent.
--
-- Idempotent (ADD COLUMN IF NOT EXISTS / CREATE TABLE IF NOT EXISTS). Run this
-- in the Supabase SQL editor AFTER Block 1's schema.sql has been applied.
--
-- Adds the review/audit surface the orchestration API writes to:
--   * fct_spec gains needs_human_review / review_reason / requested_by
--   * spec_status_history records every guarded status transition (the audit
--     log — the warehouse is the single source of truth for "who moved what,
--     when, and why"). spec_id is nullable on purpose so PRE-spec events
--     (e.g. a dedup pause or a TDM escalation, where no fct_spec exists yet)
--     can still be recorded.
-- =============================================================================

begin;

-- --- fct_spec: review + provenance columns ----------------------------------
alter table fct_spec add column if not exists needs_human_review boolean not null default false;
alter table fct_spec add column if not exists review_reason text;
alter table fct_spec add column if not exists requested_by text;   -- Slack user id of the /spec creator

comment on column fct_spec.needs_human_review is
  'Set by the hybrid classifier when confidence is low, domain/task_type is '
  'unresolved, or the transcript covers multiple projects.';
comment on column fct_spec.requested_by is
  'Slack user id that issued the /spec command (provenance for the audit log).';

-- --- spec_status_history: the transition audit log ---------------------------
create table if not exists spec_status_history (
  history_id  uuid primary key default gen_random_uuid(),
  spec_id     uuid references fct_spec (spec_id),   -- nullable: pre-spec events allowed
  from_status text,
  to_status   text,
  actor       text,
  reason      text,
  created_at  timestamptz not null default now()
);

comment on table spec_status_history is
  'Append-only audit log of spec status transitions (and pre-spec dedup events). '
  'Every guarded transition in ops/lifecycle.py writes one row here.';

create index if not exists idx_spec_status_history_spec on spec_status_history (spec_id);
create index if not exists idx_spec_status_history_created on spec_status_history (created_at);

commit;

-- NOTE: run this file once, in the Supabase SQL editor, AFTER schema.sql.
