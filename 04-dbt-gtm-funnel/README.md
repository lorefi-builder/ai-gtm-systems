# 04 — dbt GTM funnel

**The analytics layer.**

This folder is where the GTM motion described in folders 01–03 becomes
reportable. Same fictional Lorefi business — cross-media narrative discovery,
three products (Discover / Studio / Insights), per-seat pricing, self-serve
trial plus a sales-assisted enterprise motion. Folders 01–03 run the
operational loop (schema → agent → human review); this folder is what the
RevOps lead opens on Monday morning to see whether any of it is working.

## Lineage

```
                    raw_lorefi seeds (raw_leads, raw_opportunities,
                       raw_activities, raw_accounts)
                                    │
                                    ▼
                    ┌──────────────────────────────────┐
                    │  models/staging (stg_*)          │  views — clean + cast
                    └──────────────────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────────┐
                    │  models/intermediate (int_fact_*)│  tables — facts with
                    │                                  │  first/last touch and
                    │                                  │  line-item splits
                    └──────────────────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────────┐
                    │  models/marts (rpt_gtm_funnel_*) │  tables — exec-grade
                    │                                  │  reporting surface
                    └──────────────────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────────┐
                    │  snapshots (snp_opp_state)       │  SCD2 point-in-time
                    │                                  │  history of opp state
                    └──────────────────────────────────┘
```

The two top-level reports are:

- **`rpt_gtm_funnel_raw`** — one row per lead. Every stage timestamp
  (`mql_at`, `sql_at`, `opp_created_at`, `closed_at`), the derived
  `last_stage`, and the lead's total `net_bookings`. This is what a
  RevOps engineer points BI at for record-level debugging.
- **`rpt_gtm_funnel_monthly_agg`** — one row per `(month, source)`.
  Stage counts, conversion rates, average days-to-close, and total
  bookings. This is what the weekly exec deck reads from.

## How to run it

The project ships with two profiles in
[`profiles.example.yml`](./profiles.example.yml). Pick whichever fits your
environment.

### Path A — DuckDB (fast local-dev, no cloud)

```bash
pip install dbt-duckdb

cp profiles.example.yml ~/.dbt/profiles.yml
# profiles.example.yml ships with target: duckdb, so nothing to edit
# unless you want to repoint the .duckdb file location.

cd 04-dbt-gtm-funnel
dbt deps
dbt seed
dbt run
dbt snapshot
dbt test
```

That produces `./lorefi.duckdb` next to the project. Inspect it with the
DuckDB CLI:

```bash
duckdb ./lorefi.duckdb -c "SELECT month, source, mqls, sqls, opps, won, ROUND(opp_to_won_rate, 2) AS opp_to_won FROM marts.rpt_gtm_funnel_monthly_agg ORDER BY month, source;"
```

### Path B — Snowflake (production stack)

```bash
pip install dbt-snowflake

cp profiles.example.yml ~/.dbt/profiles.yml
# Edit ~/.dbt/profiles.yml: set target: snowflake and fill in the
# account / user / role / database / warehouse / schema placeholders.

cd 04-dbt-gtm-funnel
dbt deps
dbt seed
dbt run
dbt snapshot
dbt test
```

The custom `generate_schema_name` macro in
[`macros/get_custom_schema.sql`](./macros/get_custom_schema.sql) routes
each model to a clean schema (`raw`, `staging`, `intermediate`, `marts`,
`snapshots`) regardless of which target you ran against, so the Snowflake
output looks like the DuckDB output.

## What this demonstrates

The point of this folder is to make a few dbt patterns legible end-to-end:

- **Layered modeling.** Strict staging → intermediate → marts separation.
  Staging is views (cheap, transparent, recomputed on every read);
  intermediate and marts are tables (joined and aggregated, worth
  materializing).
- **CTE-driven readability.** Every non-trivial model is a chain of named
  CTEs. The intermediate model that decorates leads with touch metrics
  literally renames its CTEs `with_lead_cte → with_first_touch →
  with_last_touch → final` so a reader can scroll the file and watch the
  enrichment happen step by step.
- **Cross-database portability.** Same SQL, same dbt project, two
  warehouses. We use `DATE_TRUNC`, `SPLIT_PART`, `NULLIF`, and integer
  `date - date` subtraction — all functions that work identically in
  Snowflake and DuckDB — rather than dialect-specific helpers like
  `SAFE_DIVIDE` or `SPLIT_TO_TABLE`. The product-line fan-out uses three
  guarded `UNION ALL` branches instead of `UNNEST` for the same reason.
- **SCD2 snapshots.** `snapshots/snp_opp_state.sql` captures every
  change to an opportunity's `stage`, `amount`, or `close_date` with
  `dbt_valid_from` / `dbt_valid_to`. That is what lets you answer "what
  was Lattice Newsroom's deal worth on January 15?" months later — a
  question the live `stg_opportunities` table can never answer.
- **dbt tests as contracts.** `models/schema.yml` declares `unique` /
  `not_null` on every primary key, `relationships` on every foreign key,
  `accepted_values` on every enum, and `dbt_utils.expression_is_true`
  for the business invariants (`net_bookings >= 0`, `mql_at <= sql_at`,
  `is_won` and `is_lost` can't both be true). Run them with `dbt test`.
- **Sources with freshness.** `models/staging/_sources.yml` declares the
  raw schema and sets a freshness contract on `raw_activities`
  (`warn_after: 24h`, `error_after: 72h`) — activity volume is the
  canonical liveness signal for the upstream loader.
- **`dbt_utils` for surrogate keys.** The line-item fact table uses
  `dbt_utils.generate_surrogate_key(opp_id, product_line)` to mint a
  clean `opp_line_id` primary key without hand-rolling the hash.

## Pairs with

- **[`../01-postgres-gtm-schema/`](../01-postgres-gtm-schema/)** —
  the operational schema. In production, the `raw_lorefi.*` sources this
  dbt project consumes would be a Fivetran-replicated mirror of
  `gtm.leads`, `gtm.opportunities`, `gtm.activities`, and
  `gtm.agent_outputs` from that folder.
- **[`../02-claude-email-ops-agent/`](../02-claude-email-ops-agent/)** —
  the non-autonomous Claude agent that writes proposed subject lines into
  `gtm.agent_outputs`. The same `agent_outputs` table is what a future
  `int_agent_proposals` model in this folder would read from to track
  "what fraction of email_ops proposals got shipped last quarter?"
- **[`../03-gtm-admin-ui/`](../03-gtm-admin-ui/)** — the human review
  surface. Approve/reject decisions in that UI write to
  `gtm.agent_output_audit`, which this analytics layer would join in to
  measure reviewer throughput and per-agent acceptance rate.

## A note on lineage

This is sanitized from production dbt projects I built at **Activation
Labs**. The real projects modeled different funnels against different
client schemas — the shape (staging → intermediate → marts, SCD2 on the
opp pipeline, business-rule tests in `schema.yml`, dual local/cloud
profile) is the shape I'd reach for again in a real engagement. All
copy and the Lorefi business are fictional; the patterns are real.
