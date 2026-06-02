-- schema.sql
-- =============================================================================
-- Project Assessment Agent — data foundation (Block 1 of 4)
--
-- Internal company: Lorefi, an AI data-development firm (domain-expert data
-- labeling, model evaluation, content generation, etc.). Customers are
-- fictional firms across six industries. All data here is fictional.
--
-- LINEAGE this schema stands in for (raw -> staging -> marts):
--
--   raw            Sales-discovery call transcripts land as files / blobs.
--                  Not modeled here; referenced by raw_transcript_ref.
--
--   staging        stg_transcript_extracts -- structured fields pulled out of
--                  a single transcript by Agent 1 (the extractor) at runtime.
--                  One row per transcript. Lightly typed, jsonb-heavy.
--
--   marts          fct_spec        -- one assessed/draft spec per transcript,
--                                     with matrix color, escalation flags,
--                                     resourcing, and review status.
--                  fct_opportunity -- CRM-style opportunity spawned from an
--                                     approved spec; the revenue grain.
--                  dim_account     -- conformed customer dimension.
--                  spec_lifecycle  -- the join spine: one row stitches
--                                     transcript <-> spec <-> opportunity <->
--                                     account (<-> project) so every fact in
--                                     the marts traces back to one call.
--
--   reference      dim_capability_matrix -- the 6x6 go/no-go grid.
--                  escalation_rules      -- always-escalate overrides.
--                  spec_documents        -- RAG corpus of past 1-page specs.
--
-- In production these modeled tables are PRODUCED BY dbt (see folder 04 for the
-- pattern). For this demo the agent + dashboard read them directly from
-- Supabase; dbt is a separate artifact, not wired in here.
--
-- Target: Postgres / Supabase. Objects live in `public` so Supabase PostgREST
-- exposes them to the httpx client in backend/db/client.py with no extra config.
-- Re-runnable: drops dependents first, then recreates.
-- =============================================================================

begin;

create extension if not exists pgcrypto;  -- gen_random_uuid()

-- Clean slate (child -> parent order).
drop table if exists spec_lifecycle        cascade;
drop table if exists fct_opportunity        cascade;
drop table if exists fct_spec               cascade;
drop table if exists stg_transcript_extracts cascade;
drop table if exists spec_documents         cascade;
drop table if exists escalation_rules       cascade;
drop table if exists dim_capability_matrix  cascade;
drop table if exists dim_account            cascade;

-- ---------------------------------------------------------------------------
-- dim_account — conformed customer dimension.
-- ---------------------------------------------------------------------------
create table dim_account (
  account_id          uuid primary key default gen_random_uuid(),
  account_name        text not null,
  domain              text not null
                        check (domain in ('Technology','Financial Services',
                          'Healthcare','Legal','Retail','Government')),
  segment             text not null
                        check (segment in ('Enterprise','Mid-Market','SMB')),
  tier                text,                       -- e.g. Strategic / Growth / Standard
  region              text not null,              -- NA / EMEA / APAC / LATAM
  owner               text not null,              -- Lorefi account owner (email)
  relationship_status text not null default 'net_new'
                        check (relationship_status in
                          ('customer','net_new','reactivation')),
  created_at          timestamptz not null default now()
);

comment on table dim_account is
  'Conformed customer dimension. One row per fictional Lorefi customer.';

create index idx_dim_account_domain  on dim_account (domain);
create index idx_dim_account_segment on dim_account (segment);
create index idx_dim_account_region  on dim_account (region);

-- ---------------------------------------------------------------------------
-- dim_capability_matrix — the 6x6 go/no-go grid (domain x task_type).
-- green = standard / go, yellow = scoped / caution, red = escalate / likely no-go.
-- ---------------------------------------------------------------------------
create table dim_capability_matrix (
  domain    text not null
              check (domain in ('Technology','Financial Services','Healthcare',
                'Legal','Retail','Government')),
  task_type text not null
              check (task_type in ('Data Labeling','Model Eval','Content Gen',
                'Conversational AI','Doc Process','Code Review')),
  color     text not null check (color in ('green','yellow','red')),
  note      text,
  primary key (domain, task_type)
);

comment on table dim_capability_matrix is
  'Capability/risk grid. matrix_color on fct_spec must agree with this table '
  'for the spec''s (domain, task_type).';

-- ---------------------------------------------------------------------------
-- escalation_rules — always escalate regardless of matrix color.
-- ---------------------------------------------------------------------------
create table escalation_rules (
  rule_id   text primary key,
  label     text not null,
  detection text not null check (detection in ('deterministic','llm')),
  note      text
);

comment on table escalation_rules is
  'Override rules. If any fires for a transcript the spec is escalated even on '
  'a green cell. detection = how the flag is raised (regex/keyword vs. model).';

-- ---------------------------------------------------------------------------
-- spec_documents — RAG corpus of past ~1-page specs (the retrieval examples).
-- ---------------------------------------------------------------------------
create table spec_documents (
  doc_id     uuid primary key default gen_random_uuid(),
  domain     text not null,
  task_type  text not null,
  title      text not null,
  body       text not null,          -- full markdown spec
  created_at timestamptz not null default now()
);

comment on table spec_documents is
  'Past approved specs used as few-shot / retrieval context by the drafting agent.';

create index idx_spec_documents_domain_task
  on spec_documents (domain, task_type);

-- ---------------------------------------------------------------------------
-- fct_spec — one assessed/draft spec per transcript (the assessment grain).
-- ---------------------------------------------------------------------------
create table fct_spec (
  spec_id          uuid primary key default gen_random_uuid(),
  transcript_id    text not null,
  account_id       uuid not null references dim_account (account_id),
  domain           text not null,
  task_type        text not null,
  matrix_color     text not null check (matrix_color in ('green','yellow','red')),
  escalation_flags jsonb not null default '[]'::jsonb,  -- array of rule_id
  confidence       numeric(4,3) not null
                     check (confidence >= 0 and confidence <= 1),
  ec_count         integer not null default 0,  -- expert contributors
  tdm_count        integer not null default 0,  -- technical delivery managers
  dops_count       integer not null default 0,  -- data ops
  fde_count        integer not null default 0,  -- forward-deployed engineers
  resource_flags   jsonb not null default '{}'::jsonb,
  status           text not null default 'draft'
                     check (status in ('draft','in_review','approved','rejected')),
  rejection_reason text,                          -- null unless status='rejected'
  opportunity_id   uuid,                          -- soft link; spine lives in
                                                  -- spec_lifecycle (avoids the
                                                  -- circular fk with fct_opportunity)
  created_at       timestamptz not null default now(),
  approved_at      timestamptz,                   -- null unless approved
  -- matrix color must exist for this (domain, task_type) cell.
  foreign key (domain, task_type)
    references dim_capability_matrix (domain, task_type)
);

comment on table fct_spec is
  'One go/no-go assessment + draft spec per discovery transcript.';
comment on column fct_spec.opportunity_id is
  'Soft reference to fct_opportunity. The enforced join lives in spec_lifecycle '
  'to avoid a circular FK (opportunities reference the spec that spawned them).';

create index idx_fct_spec_account     on fct_spec (account_id);
create index idx_fct_spec_status      on fct_spec (status);
create index idx_fct_spec_domain_task on fct_spec (domain, task_type);
create index idx_fct_spec_created_at  on fct_spec (created_at);
create index idx_fct_spec_transcript  on fct_spec (transcript_id);

-- ---------------------------------------------------------------------------
-- fct_opportunity — CRM opportunity spawned from an APPROVED spec (revenue grain).
-- ---------------------------------------------------------------------------
create table fct_opportunity (
  opportunity_id uuid primary key default gen_random_uuid(),
  spec_id        uuid not null references fct_spec (spec_id),
  account_id     uuid not null references dim_account (account_id),
  name           text not null,
  stage          text not null
                   check (stage in ('Discovery','Proposal','Negotiation',
                     'Closed Won','Closed Lost')),
  amount         numeric(12,2) not null default 0,
  segment        text not null,        -- denormalized from account for fast slicing
  region         text not null,        -- denormalized from account
  owner          text not null,
  created_at     timestamptz not null default now(),
  closed_at      timestamptz,          -- null unless Closed Won/Lost
  is_won         boolean not null default false
);

comment on table fct_opportunity is
  'Opportunity created only from approved specs. segment/region denormalized '
  'from dim_account so the dashboard can slice win rates without a join.';

create index idx_fct_opportunity_spec    on fct_opportunity (spec_id);
create index idx_fct_opportunity_account on fct_opportunity (account_id);
create index idx_fct_opportunity_stage   on fct_opportunity (stage);
create index idx_fct_opportunity_segment on fct_opportunity (segment);
create index idx_fct_opportunity_region  on fct_opportunity (region);

-- ---------------------------------------------------------------------------
-- spec_lifecycle — the join spine. One row per transcript stitches every grain.
-- ---------------------------------------------------------------------------
create table spec_lifecycle (
  lifecycle_id   uuid primary key default gen_random_uuid(),
  transcript_id  text not null,
  spec_id        uuid not null references fct_spec (spec_id),
  opportunity_id uuid references fct_opportunity (opportunity_id),  -- null until won/created
  account_id     uuid not null references dim_account (account_id),
  project_id     uuid,                 -- null; delivery project (future block)
  created_at     timestamptz not null default now()
);

comment on table spec_lifecycle is
  'Spine: transcript_id <-> spec_id <-> opportunity_id <-> account_id. IDs are '
  'consistent across fct_spec / fct_opportunity / dim_account.';

create unique index uq_spec_lifecycle_spec on spec_lifecycle (spec_id);
create index idx_spec_lifecycle_transcript on spec_lifecycle (transcript_id);
create index idx_spec_lifecycle_account    on spec_lifecycle (account_id);
create index idx_spec_lifecycle_opp        on spec_lifecycle (opportunity_id);

-- ---------------------------------------------------------------------------
-- stg_transcript_extracts — staging. Populated at RUNTIME by Agent 1.
-- Empty after seeding; shown here so the schema is complete.
-- ---------------------------------------------------------------------------
create table stg_transcript_extracts (
  extract_id          uuid primary key default gen_random_uuid(),
  transcript_id       text not null,
  account_name        text,
  domain_signals      jsonb not null default '{}'::jsonb,
  candidate_task_type text,
  data_characteristics jsonb not null default '{}'::jsonb,
  scope               jsonb not null default '{}'::jsonb,
  success_criteria    jsonb not null default '{}'::jsonb,
  special_flags       jsonb not null default '[]'::jsonb,
  raw_transcript_ref  text,                 -- pointer back into raw (file/blob)
  created_at          timestamptz not null default now()
);

comment on table stg_transcript_extracts is
  'Staging output of the transcript-extraction agent. One row per transcript; '
  'jsonb fields hold loosely-structured signals before they harden into fct_spec.';

create index idx_stg_extracts_transcript on stg_transcript_extracts (transcript_id);

commit;
