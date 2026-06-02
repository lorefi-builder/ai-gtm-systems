-- migration_block5a.sql
-- =============================================================================
-- Block 5A: regenerate flow, soft-delete, and spec lineage.
--
-- Idempotent. Run in the Supabase SQL editor AFTER schema.sql (Block 1) and
-- migration_block3.sql (Block 3).
--
-- Adds to fct_spec:
--   * regenerated_from   -- self-reference to the rejected spec a draft was
--                           regenerated from (lineage + learning signal)
--   * correction_context -- optional <=500-char creator guidance at regeneration
-- Extends the status CHECK to allow 'deleted' (soft delete). spec_status_history
-- (Block 3) remains the state-over-time audit record; no SCD2 table is needed.
-- =============================================================================

begin;

-- --- lineage columns ---------------------------------------------------------
alter table fct_spec add column if not exists regenerated_from uuid;
alter table fct_spec add column if not exists correction_context text;

comment on column fct_spec.regenerated_from is
  'The rejected spec_id this draft was regenerated from (null for first-pass specs).';
comment on column fct_spec.correction_context is
  'Optional <=500-char creator guidance supplied at /regenerate; fed to the '
  'drafter as additional contributor-style guidance (semantic signal).';

-- Self-referential FK for lineage integrity (idempotent via catalog check).
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'fct_spec_regenerated_from_fkey'
  ) then
    alter table fct_spec
      add constraint fct_spec_regenerated_from_fkey
      foreign key (regenerated_from) references fct_spec (spec_id);
  end if;
end
$$;

create index if not exists idx_fct_spec_regenerated_from on fct_spec (regenerated_from);

-- --- length guard on correction_context (<=500) ------------------------------
alter table fct_spec drop constraint if exists fct_spec_correction_context_len;
alter table fct_spec add constraint fct_spec_correction_context_len
  check (correction_context is null or char_length(correction_context) <= 500);

-- --- extend the status CHECK to allow 'deleted' (drop + re-add = re-runnable) -
alter table fct_spec drop constraint if exists fct_spec_status_check;
alter table fct_spec add constraint fct_spec_status_check
  check (status in ('draft', 'in_review', 'approved', 'rejected', 'deleted'));

commit;

-- NOTE: run this file once, in the Supabase SQL editor, AFTER schema.sql
-- (Block 1) and migration_block3.sql (Block 3).
