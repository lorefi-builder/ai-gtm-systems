# 02 — Claude email-ops agent

**The agent proposes. A human approves. The database enforces.**

This is a non-autonomous Claude agent that watches for underperforming
subject-line A/B tests in the [Lorefi GTM schema](../01-postgres-gtm-schema/)
and proposes two new subject-line candidates per losing variant. Every output
is written to `gtm.agent_outputs` with `status='pending_review'` — the agent
literally cannot ship its own work, both because it never tries to and
because the database role it authenticates as (`gtm_agent`) is denied that
privilege by RLS.

## The headline: human-in-the-loop, by design

Nothing this agent emits reaches a customer without a person on the
`gtm_admin` side pulling it off the `pending_review` queue and approving it.
This is not a soft convention — it is enforced in three places:

1. **The agent never sets `status` directly.** Every INSERT relies on the
   column default (`pending_review`).
2. **The RLS policy on `gtm.agent_outputs`** rejects any INSERT from
   `gtm_agent` whose `status` is anything other than `pending_review`. Even
   a misbehaving prompt or a corrupted payload cannot ship a row.
3. **The `BEFORE UPDATE OF status` trigger** rejects illegal state transitions,
   so a different process cannot launder a proposal into `shipped` without
   going through `approved` first.

If the LLM hallucinates a subject line that's off-brand, the worst-case
outcome is a row in a review queue. That is the whole point of the design.

## DRY_RUN safety

The agent ships with `DRY_RUN=true` in `.env.example`. In dry-run mode it:

- Reads the database (the `SELECT`s, fine).
- Calls Claude and validates the proposed JSON.
- Prints the would-be payload to stdout.
- **Does not write to `gtm.agent_outputs`.**

You have to explicitly set `DRY_RUN=false` before any row lands in the
queue. Treat `DRY_RUN=false` as the equivalent of going from staging to
production.

## What it actually does

```
                                      ┌──────────────────────┐
                                      │  gtm.experiments     │
                                      │  primary_metric =    │
                                      │     'open_rate'      │
                                      └──────────┬───────────┘
                                                 │
                              ┌──────────────────┴──────────────────┐
                              │  gtm.experiment_variants            │
                              │   (losing, non-control)             │
                              └──────────────────┬──────────────────┘
                                                 │
                       ┌─────────────────────────┴─────────────────────────┐
                       │  open_rate =  COUNT(distinct opener leads)        │
                       │             ───────────────────────────────────   │
                       │               COUNT(*) FROM exposures             │
                       │  (numerator: gtm.activities WHERE                 │
                       │    activity_type = 'email_opened'                 │
                       │    AND occurred_at >= exposed_at)                 │
                       └─────────────────────────┬─────────────────────────┘
                                                 │
                          filter: open_rate < OPEN_RATE_THRESHOLD
                                  AND sample_size >= MIN_SAMPLE_SIZE
                                                 │
                                                 ▼
                                  Claude (claude-sonnet-4-6)
                                  system prompt = brand voice
                                  user prompt   = experiment context
                                                 │
                                                 ▼
                              {two ProposedSubjectLine objects}
                                                 │
                                                 ▼
                          INSERT INTO gtm.agent_outputs (…)
                          status defaults to 'pending_review'
```

## Brand-safety constraints (enforced in the prompt + schema)

The system prompt locks these in; the zod schema in
[`src/schema.ts`](src/schema.ts) double-checks them post-response and throws
on violation rather than letting an off-spec proposal land in the queue:

- **Max 60 characters** per subject line.
- **No emojis.**
- Must include `Lorefi` or one of the product names (`Discover`, `Studio`,
  `Insights`).
- Each pair must vary the *approach* — curiosity vs. proof vs. urgency vs.
  personalization — not just synonyms.
- `predicted_lift_qualitative` ∈ `{low, medium, high}`. Calibrated honestly.
- JSON only, no preamble, no backticks. Anything else fails validation.

## Run it locally

1. **Set up the schema** in
   [`../01-postgres-gtm-schema/`](../01-postgres-gtm-schema/) against a local
   Postgres. Follow that folder's README for `createdb`, migrations, and
   `seeds/lorefi_seed.sql`.

2. **Configure this folder:**

   ```bash
   cd 02-claude-email-ops-agent
   cp .env.example .env
   # then edit .env and fill in:
   #   ANTHROPIC_API_KEY  — from console.anthropic.com
   #   DATABASE_URL       — point at the local lorefi_gtm DB, ideally as gtm_agent
   ```

3. **Install and run:**

   ```bash
   pnpm install
   pnpm dev          # tsx src/index.ts — dry-run by default
   ```

   To actually write proposals into `gtm.agent_outputs`, set `DRY_RUN=false`
   in `.env` and run again. The inserted row's id will be printed to stdout.

4. **Inspect what landed:**

   ```sql
   SELECT id, agent_name, target_ref, status, created_at,
          jsonb_pretty(payload) AS payload
   FROM gtm.agent_outputs
   WHERE agent_name = 'email_ops'
   ORDER BY created_at DESC
   LIMIT 5;
   ```

## Layout

```
02-claude-email-ops-agent/
├── package.json
├── tsconfig.json
├── .env.example
├── prompts/
│   ├── system.md           -- brand voice + hard constraints + JSON contract
│   └── user-template.md    -- {{mustache}} context injection
└── src/
    ├── config.ts           -- env parsing with zod
    ├── db.ts               -- pg pool + transaction wrapper
    ├── schema.ts           -- zod schemas for proposals + DB rows
    ├── queue.ts            -- the open-rate CTE + writeAgentOutput
    ├── agent.ts            -- Claude call + strict JSON validation
    └── index.ts            -- orchestrator
```

## A note on lineage

This is sanitized from a production pattern I built at **Activation Labs**.
All client references, real prompts, real schema, and real campaigns have
been replaced with the fictional Lorefi context that runs through this
portfolio. The shape of the design — agent role + RLS + queue table +
DRY_RUN gate + strict-JSON Claude calls + zod validation — is the same
shape I'd reach for again in a real engagement.
