# AI-Native GTM Systems

The inside of an AI-native GTM system, end-to-end.

Sanitized patterns from production engagements at Activation Labs,
demonstrated against a fictional B2B SaaS company called **Lorefi**
(cross-media narrative discovery). Same Lorefi across every folder —
the repo reads as one coherent system, not four loose demos.

## What's inside

| Folder | What it shows | Stack |
|---|---|---|
| [`01-postgres-gtm-schema/`](./01-postgres-gtm-schema) | Production GTM data model — leads, activities, experiments, agent-output queue. Defense-in-depth status enforcement (CHECK + transition trigger + RLS), audit log via trigger, idempotent funnel advancement for out-of-order events. | PostgreSQL |
| [`02-claude-email-ops-agent/`](./02-claude-email-ops-agent) | Non-autonomous TypeScript Claude agent. Watches for underperforming subject-line A/B tests via a 3-CTE open-rate query, proposes two new candidates per losing variant, writes them to the queue as `pending_review`. Never ships its own output — the database role denies it. | TypeScript, Claude API |
| [`03-gtm-admin-ui/`](./03-gtm-admin-ui) | Next.js 15 admin surface at `/gtm-admin/queue` where humans approve or reject agent outputs. Server actions with row-level race-condition guards, optimistic UI with snap-back on failure, typed errors surfaced as toasts. | TypeScript, Next.js |
| [`04-dbt-gtm-funnel/`](./04-dbt-gtm-funnel) | End-to-end dbt project — staging → intermediate → marts → snapshots — for a B2B SaaS GTM funnel. Cross-warehouse portable (Snowflake + DuckDB), 40+ tests as contracts, SCD2 historical tracking. | dbt, SQL |

## The pattern

I ship AI-native GTM engines inside client codebases — funnel, agents,
analytics, and kill thresholds — installed in 4–6 weeks via Claude Code.
This repo demonstrates each layer in isolation against Lorefi.

The headline design choice across all four folders:
**agents propose, humans approve, the database enforces.**

## Who I am

Kitwanie Carbon, operator, tinkerer, product builder.
Six years scaling GTM analytics at Tebra, Grafana Labs, Miro, and
HashiCorp.

[LinkedIn](https://www.linkedin.com/in/kitwanie-carbon/)
