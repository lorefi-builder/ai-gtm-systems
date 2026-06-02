# Sync model & flagged assumptions (Block 3)

A short reference for the slide deck + flowchart. Captures the architecture
principle this orchestration layer encodes and the assumptions baked into it.

## Hub-and-spoke: the warehouse is the single source of truth

```
                         ┌──────────────────────────┐
                         │   DATA WAREHOUSE (hub)    │
                         │        Supabase           │
                         │  single source of truth   │
                         │   + single audit log      │
                         └──────────────────────────┘
                          ▲      ▲            ▲     │
            writes/reads  │      │            │     │  reads/writes
              ┌───────────┘      │            │     └───────────┐
              │                  │            │                 │
        ┌──────────┐      ┌────────────┐  ┌────────────┐  ┌────────────┐
        │  Slack   │      │   Admin UI │  │ Salesforce │  │  Pipeline  │
        │ (spoke)  │      │  (spoke)   │  │  (spoke)   │  │ dedup +    │
        └──────────┘      └────────────┘  └────────────┘  │ Agent 1/2  │
                                                          └────────────┘
```

- Every state change is a **warehouse row mutation** you can query. Nothing is
  reconstructed from chat text, and nothing is sourced from a notification
  surface — Slack/UI/Salesforce are **spoke clients** that read from and write to
  the warehouse, never directly to each other.
- The admin dashboard reads **warehouse models only** (`fct_spec`,
  `fct_opportunity`, `spec_lifecycle`, `dim_account`, `spec_status_history`).
- The **spec pipeline (dedup + Agent 1/2) runs real-time off the warehouse** and
  has **no dependency on either Salesforce sync leg**.

## Asymmetric sync model

| Leg | Direction | Tool | Cadence | Why |
|-----|-----------|------|---------|-----|
| **Inbound ETL** | Salesforce → warehouse | **Fivetran** | Scheduled **batch** — hourly in business hours + an overnight full reconcile (~every 4–6h effective) | Pulls opp stage / amount / close_date so the dashboard funnel reflects CRM reality. **Not latency-sensitive.** |
| **Outbound reverse ETL** | warehouse → Salesforce | **Hightouch** (or Census; Fivetran's reverse-ETL could consolidate both under one vendor) | **Event-driven / near-real-time**, triggered **on spec approval** | Pushes the new Spec object + Opportunity object to SF within minutes so a rep isn't waiting on a batch. **Latency-sensitive (a human is waiting).** |

**Why asymmetric:** the write path (approval → SF) is latency-sensitive, so it's
event-driven; the read path (SF stage changes → dashboard) is not, so it's
cheaper scheduled batch. Uniform real-time would be over-engineered at this scale
(mid-stage enterprise, hundreds of opportunities).

## How this demo stands in for production

FastAPI plays the role of all orchestration triggers and both sync legs. Each
stand-in is commented in code with the production mechanism it replaces:

- `POST /spec` → **Slack slash command**; the `stg_transcript_extracts` insert
  fires dedup + Agent 2 via a **Postgres LISTEN/NOTIFY trigger** (or Supabase
  Edge Function / queue).
- `POST /approve` fan-out (create opportunity + spine) → **Hightouch reverse ETL**
  (warehouse → SF), event-driven on approval.
- `GET /dashboard-data` opp-stage figures → kept fresh in production by
  **Fivetran inbound batch** (SF → warehouse).

## FLAGGED ASSUMPTIONS (confirm with the team)

1. **Opp created ON APPROVAL**, not at discovery. If Snorkel/CRM practice creates
   the opportunity at disco instead, `/approve` becomes *link-and-advance* rather
   than *create*. (Confirming.)
2. **Reverse ETL (warehouse → SF)** is event-driven / near-real-time on approval;
   **ETL (SF → warehouse)** is scheduled batch ~every 4–6h (business-hours +
   nightly reconcile).
3. **Dashboard opp-stage data is eventually consistent** — fresh as of the last
   inbound sync (hours-scale). Acceptable for pipeline reporting; surfaced to the
   user via the `data_freshness` field on `/dashboard-data`.
4. **Sync layer is managed connectors** (Fivetran inbound, Hightouch/Census
   outbound), assumed **not built**. The demo simulates approval → SF with a
   direct warehouse write.
5. **Dedup correctness does NOT depend on Salesforce freshness** — it reads
   warehouse spec history directly, real-time.
6. **Custom SF objects exist:** a **Spec** object + standard **Opportunity**,
   linkable back to warehouse `spec_id` / `opportunity_id`.
