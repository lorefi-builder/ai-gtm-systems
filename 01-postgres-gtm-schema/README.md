# 01 — Postgres GTM schema

**Agents propose, humans approve, the database enforces.**

This folder is the data foundation for an agentic GTM stack at *Lorefi*, a
(fictional) cross-media narrative-discovery platform for B2B media teams.
Lorefi ships three products (Discover, Studio, Insights), prices per seat,
and runs a self-serve trial plus a sales-assisted enterprise motion.

The schema lives in a single Postgres namespace, `gtm`. It is designed so
that autonomous agents can safely participate in the funnel — proposing
subject-line variants, blog drafts, ad copy, social captions — without
shipping anything until a human reviewer approves it. The database itself
enforces that contract.

## What's in here

```
01-postgres-gtm-schema/
├── migrations/
│   ├── 001_init.sql                -- extensions, schema, roles, helpers
│   ├── 002_leads.sql               -- leads + activities + RLS
│   ├── 003_experiments.sql         -- experiments / variants / exposures
│   ├── 004_agent_queue.sql         -- agent_outputs queue + state machine
│   └── 005_triggers_and_audit.sql  -- audit log + funnel advancement
├── seeds/
│   └── lorefi_seed.sql             -- 30 leads, ~125 activities, 3 exps,
│                                      6 variants, 15 agent_outputs
├── docs/
│   └── schema-diagram.md           -- ASCII ERD + state machine
└── README.md
```

## Design choices

### A queue table, not a queue *system*

`gtm.agent_outputs` is a plain table with a `status` column and an
`(agent_name, created_at DESC)` index. There is no SQS, no Pub/Sub, no
separate worker queue. Two reasons:

1. **Review is an interactive workflow.** The "queue UI" is just
   `WHERE status = 'pending_review' ORDER BY created_at` — a query, not a
   message consumer. Latency matters less than auditability.
2. **The proposals *are* the artifact.** They need to be queryable forever
   for analysis ("what fraction of email_ops proposals got shipped last
   quarter?"). A queue would discard them after consumption.

The index `idx_agent_outputs_status` keeps the queue read cheap even as the
table grows; the partial-friendly cardinality of `status` means it stays
selective for `pending_review` specifically.

### A `CHECK`-and-trigger pair for status transitions

The status state machine is:

```
pending_review ─► approved ─► shipped     (both rejected and shipped are terminal)
              └► rejected
```

Enforcement is layered:

- A **value `CHECK`** on `status` blocks made-up states.
- A **coherence `CHECK`** ties `reviewed_at` / `shipped_at` to the
  corresponding states — you can't be `shipped` without a `shipped_at`.
- A **`BEFORE UPDATE OF status` trigger** (`enforce_agent_output_transition`)
  rejects illegal old→new transitions. `CHECK` constraints can't see `OLD`,
  so transitions specifically have to live in a trigger.

The reason this matters: the agent role *can* INSERT proposals but cannot
mutate them past `pending_review`, and even a misbehaving admin script
cannot turn a `rejected` row into `shipped`. The state machine is
load-bearing, so we encode it where it can't be skipped.

### RLS for the agent role

`gtm_agent` is the role agents authenticate as. Its powers, by table:

| table             | SELECT | INSERT                       | UPDATE | DELETE |
|-------------------|--------|------------------------------|--------|--------|
| `leads`           | ✓      | —                            | —      | —      |
| `activities`      | ✓      | —                            | —      | —      |
| `experiments*`    | ✓      | —                            | —      | —      |
| `agent_outputs`   | ✓      | ✓ (with `status='pending_review'`) | — | — |
| `agent_output_audit` | ✓   | —                            | —      | —      |

The `INSERT` privilege on `agent_outputs` is tightened by an RLS policy:

```sql
CREATE POLICY p_agent_outputs_agent_insert ON gtm.agent_outputs
  FOR INSERT TO gtm_agent WITH CHECK (status = 'pending_review');
```

So even if an agent passes `status='shipped'` in its INSERT, the row is
rejected. The agent literally cannot ship its own output. This is the
"database enforces" half of the headline — not a policy in application
code that someone might forget.

### `updated_at` via a single trigger function

`gtm.set_updated_at()` is attached as a `BEFORE UPDATE` trigger on every
table. One function, idempotent migrations (`DROP TRIGGER IF EXISTS ...
CREATE TRIGGER`), no per-table bookkeeping.

### Idiomatic Postgres

- UUID primary keys via `gen_random_uuid()` (from `pgcrypto`).
- `jsonb` for activity payloads and agent output content — schema-flexible
  where it should be, and indexable when we need it.
- A `STORED` generated column (`leads.email_domain`) for the common
  "aggregate by company domain" query.
- `CASCADE` on most FKs because activity/exposure rows have no meaning
  without their parent lead.

## Running locally

```bash
# 1. Create the database
createdb lorefi_gtm

# 2. Apply migrations in order
for f in migrations/00{1,2,3,4,5}_*.sql; do
  echo ">> $f"
  psql -d lorefi_gtm -v ON_ERROR_STOP=1 -f "$f"
done

# 3. Seed
psql -d lorefi_gtm -v ON_ERROR_STOP=1 -f seeds/lorefi_seed.sql

# 4. Sanity-check
psql -d lorefi_gtm <<'SQL'
SELECT funnel_state, count(*) FROM gtm.leads GROUP BY 1 ORDER BY 1;
SELECT status, count(*) FROM gtm.agent_outputs GROUP BY 1 ORDER BY 1;
SELECT count(*) AS audit_rows FROM gtm.agent_output_audit;
SQL
```

Expected after seeding:

- `gtm.leads`: 30 rows, distributed across `anonymous / known / mql / sql /
  opp / won / lost`.
- `gtm.agent_outputs`: 15 rows — 5 `pending_review`, 3 `approved`,
  3 `rejected`, 4 `shipped`.
- `gtm.agent_output_audit`: 26 rows (15 inserts + 7 → approved + 3 →
  rejected + 4 → shipped).

To inspect the state machine in action:

```sql
SELECT a.created_at, a.agent_name, a.payload->>'slug' AS slug,
       a.status, a.shipped_ref
FROM gtm.agent_outputs a
ORDER BY a.created_at;

SELECT o.payload->>'slug' AS slug,
       au.changed_at, au.old_status, au.new_status, au.changed_by
FROM gtm.agent_output_audit au
JOIN gtm.agent_outputs o ON o.id = au.output_id
ORDER BY o.created_at, au.changed_at;
```

To try a denied transition (this should error with `check_violation`):

```sql
SET ROLE gtm_admin;
UPDATE gtm.agent_outputs
SET status = 'shipped', shipped_at = now(), shipped_ref = 'cheat'
WHERE payload->>'slug' = 'p1';  -- still pending_review; can't jump to shipped
```

To try the RLS guard (also expected to fail):

```sql
SET ROLE gtm_agent;
INSERT INTO gtm.agent_outputs (agent_name, output_type, payload, status)
VALUES ('email_ops', 'subject_line_variant',
        '{"subject_line":"Bypass"}', 'approved');
RESET ROLE;
```

## What consumes this schema

The next two folders in this portfolio sit on top of this schema:

- **`../02-email-ops-agent/`** — reads `gtm.leads`, `gtm.activities`,
  `gtm.experiments`, and the open variants on each, and INSERTs proposed
  subject-line variants into `gtm.agent_outputs` as `pending_review`. It
  authenticates as `gtm_agent`, so the database is what stops it from
  shipping unreviewed copy — not the agent's prompt.
- **`../03-content-ops-agent/`** — does the same shape of work for blog
  drafts, ad copy, and social captions, targeting topics rather than
  experiments via `agent_outputs.target_ref`.

A separate human-facing reviewer UI (not in this repo) authenticates as
`gtm_admin`, reads `WHERE status = 'pending_review'`, and is the only
caller that can flip rows to `approved` / `rejected` / `shipped`. The
audit log in `gtm.agent_output_audit` is the canonical record of who
approved what and when.
