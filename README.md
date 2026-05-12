# AI-Native GTM Systems

The inside of an AI-native GTM system, end-to-end.

Sanitized patterns from production engagements at Activation Labs,
demonstrated against a fictional B2B SaaS company called **Lorefi**
(cross-media narrative discovery). Same Lorefi across every folder —
the repo reads as one coherent system, not four loose demos.

## What's inside

| Folder | What it shows | Stack |
|---|---|---|
| [`01-postgres-gtm-schema/`](./01-postgres-gtm-schema) | Production GTM data model — funnel state, experiments, an agent-output queue with human approval, RLS for multi-tenant safety. | PostgreSQL |
| [`02-claude-email-ops-agent/`](./02-claude-email-ops-agent) | A scheduled Claude agent that proposes email subject-line variants, writes drafts into the Postgres queue, never ships autonomously. | TypeScript, Claude API |
| [`03-gtm-admin-ui/`](./03-gtm-admin-ui) | Next.js admin surface at `/gtm-admin/queue` where humans approve/reject agent outputs. The other half of the loop. | TypeScript, Next.js |
| [`04-dbt-gtm-funnel/`](./04-dbt-gtm-funnel) | End-to-end dbt project — staging → intermediate → marts → snapshots — for a B2B SaaS GTM funnel with SCD2 historical tracking. | dbt, SQL |

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

[LinkedIn](https://linkedin.com/in/kitwaniecarbon)
