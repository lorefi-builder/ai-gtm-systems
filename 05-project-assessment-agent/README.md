# Project Assessment Agent

Turns sales-discovery transcripts into **go/no-go assessments** and **draft
project specs** for **Lorefi**, a (fictional) AI data-development company —
domain-expert data labeling, model evaluation, content generation, and the
like. Customers are invented firms across six industries. All data here is
fictional.

This folder is **Block 1 of 4: the data foundation** — schema, capability
matrix, seed data, and a thin DB client. No agents or API yet (those are later
blocks).

The flow the finished system implements:

1. A discovery-call transcript comes in.
2. **Agent 1 (extractor)** pulls structured signals → `stg_transcript_extracts`.
3. **Agent 2 (assessor)** reads the signals, looks up the **capability matrix**
   and **escalation rules**, retrieves similar past specs from `spec_documents`,
   and writes a go/no-go assessment + draft spec → `fct_spec`.
4. Approved specs spawn `fct_opportunity` rows; the whole chain is stitched by
   `spec_lifecycle`.

## Data lineage

```
  raw                staging                     marts
  ───                ───────                     ─────

  discovery   ──►  stg_transcript_extracts ──►  fct_spec ──┬──► fct_opportunity
  transcript       (Agent 1 output,             (Agent 2   │     (approved specs
  (file/blob)       one row per transcript)      output)   │      only; revenue grain)
                                                            │
                                                            ▼
                                                     spec_lifecycle  ◄── the join spine
                                                     (transcript ↔ spec ↔
                                                      opportunity ↔ account)

  reference / conformed
  ─────────────────────
  dim_account            dim_capability_matrix   escalation_rules   spec_documents
  (customers)            (6×6 go/no-go grid)     (always-escalate)  (RAG corpus)
```

`dim_account` joins to `fct_spec`, `fct_opportunity`, and `spec_lifecycle` by
`account_id`. The capability matrix backs `fct_spec.matrix_color` via a
composite FK on `(domain, task_type)`.

> **Production note:** the demo reads these modeled tables **directly from
> Supabase**. In production, **dbt** is the producer of the `dim_`/`fct_`/`stg_`
> tables (see folder `04-dbt-gtm-funnel` for that pattern) — a separate artifact,
> not wired into this block.

## Tables

| Table | Layer | Purpose |
|-------|-------|---------|
| `dim_account` | mart (dim) | Conformed customer dimension — one row per fictional Lorefi customer. |
| `dim_capability_matrix` | reference | The 6×6 capability/risk grid; `color` drives the go/no-go call. |
| `escalation_rules` | reference | Overrides that always escalate regardless of matrix color. |
| `spec_documents` | reference | RAG corpus of past ~1-page specs (retrieval examples). |
| `stg_transcript_extracts` | staging | Agent 1's structured pull from a single transcript (populated at runtime). |
| `fct_spec` | mart (fact) | One go/no-go assessment + draft spec per transcript. |
| `fct_opportunity` | mart (fact) | CRM opportunity spawned from an approved spec (revenue grain). |
| `spec_lifecycle` | mart (spine) | Joins transcript ↔ spec ↔ opportunity ↔ account. |

## Capability matrix

`backend/matrix/capability_matrix.json` is the source of truth for the grid
(task-type order: Data Labeling, Model Eval, Content Gen, Conversational AI,
Doc Process, Code Review) and the five escalation rules. The seed loads it into
`dim_capability_matrix` / `escalation_rules`, and `fct_spec.matrix_color` always
agrees with it.

- **green** — standard delivery / go
- **yellow** — deliverable with scoping + caveats
- **red** — escalate / likely no-go
- **escalation rules** (PII/regulated, non-English, non-standard platform,
  extreme complexity, new audio/video modality) fire *regardless* of color.

## Layout

```
05-project-assessment-agent/
├── README.md
├── .env.example
├── backend/
│   ├── requirements.txt
│   ├── db/
│   │   ├── schema.sql            # Postgres DDL for Supabase
│   │   └── client.py             # httpx PostgREST client (service key, server-side)
│   └── matrix/
│       └── capability_matrix.json
└── seed/
    ├── seed_data.py              # generates + inserts fictional data (you run it)
    └── transcripts/
        └── sample_transcript_01.md
```

## How to run

1. **Apply the schema.** In the Supabase **SQL editor**, paste and run
   `backend/db/schema.sql`. (It is re-runnable — it drops and recreates.)

2. **Configure env.** Copy the template and fill in your project values:

   ```bash
   cp .env.example .env
   # set SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY
   ```

   The service key bypasses RLS — **server-side only**, never ship it to a client.

3. **Install deps** (a virtualenv is recommended):

   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Seed.** This generates ~41 accounts, the matrix + rules, 12 RAG specs,
   ~160 `fct_spec`, ~90 `fct_opportunity`, and the lifecycle spine, then inserts
   everything via the PostgREST client:

   ```bash
   python seed/seed_data.py
   ```

   It is deterministic (fixed seed + fixed "now"), so re-running reproduces the
   same ids and numbers. `stg_transcript_extracts` stays empty — it's populated
   at runtime by Agent 1 in a later block.

Drop additional discovery transcripts into `seed/transcripts/` for the pipeline
to run on once the agents land.
