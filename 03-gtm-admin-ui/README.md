# 03 — GTM admin UI

**The human side of the loop.**

The visual identity uses Activation Labs' phoenix-themed brand palette
(Lunar New Year red, burgundy, orange, antique gold, warm cream) on a Fraunces /
IBM Plex Sans / IBM Plex Mono type stack. The approval card was redesigned to
read as a reviewer interface — typed proposal cards with source context, an
A/B layout for paired email subject lines, and a qualified lift pill — rather
than a JSON inspector.

This is folder 03 — the UI where humans approve or reject what the agent in
[folder 02](../02-claude-email-ops-agent/) proposed. Close the loop by reading
this README and then running the dev server.

Together with folder 01 (the schema and state machine) and folder 02 (the
agent that proposes), this folder is the last piece of the
agents-propose / humans-approve / database-enforces design. Nothing reaches
a customer until somebody pulls a row out of `pending_review` here.

## The loop

```
                      [folder 02 agent]
                            │
                            │  INSERT status='pending_review'
                            ▼
                ┌──────────────────────────────┐
                │  gtm.agent_outputs           │  (folder 01)
                └──────────────────────────────┘
                            │
                            │  SELECT WHERE status='pending_review'
                            ▼
                ┌──────────────────────────────┐
                │  /gtm-admin/queue            │  (this folder)
                └──────────────────────────────┘
                            │
                            │  UPDATE status='approved' | 'rejected'
                            ▼
                ┌──────────────────────────────┐
                │  folder 01 trigger writes to │
                │  gtm.agent_output_audit      │
                └──────────────────────────────┘
```

The agent in folder 02 authenticates as `gtm_agent` and is *barred by RLS*
from writing any status other than `pending_review`. This UI is the only
caller that can flip a row to `approved` / `rejected` — and the database's
own trigger (`enforce_agent_output_transition` in
[`migrations/004_agent_queue.sql`](../01-postgres-gtm-schema/migrations/004_agent_queue.sql))
is what enforces the legal transitions on top of the application's intent.

## Pairs with

- **[`../01-postgres-gtm-schema/`](../01-postgres-gtm-schema/)** — the
  `gtm.agent_outputs` queue table, status state machine, RLS policies, and
  audit log this UI mutates against.
- **[`../02-claude-email-ops-agent/`](../02-claude-email-ops-agent/)** — the
  non-autonomous Claude agent that inserts the rows this UI reviews.

## What this app actually is

A minimal Next.js 15 (app router) surface at `/gtm-admin/queue`:

- **Server-component query.** `app/gtm-admin/queue/page.tsx` is an async
  RSC that selects all `pending_review` rows ordered by `created_at DESC`
  and groups them by `agent_name`.
- **Two sections.** "Email Ops queue" and "Content Ops queue" each render
  with a mono-font count badge and empty state.
- **Client-side approval card.** Each row renders as a card with the
  pretty-printed `payload` JSON, the agent and output-type pills, the
  target reference, and Approve / Reject controls.
- **Server actions for mutations.** `actions.ts` exposes `approveOutput`
  and `rejectOutput`, both guarded by a `WHERE status = 'pending_review'`
  clause that prevents a double-action race where two reviewers click on
  the same card.
- **Optimistic UI.** The card animates out the moment you click Approve or
  Reject. If the server action fails (typically because someone else
  already actioned the row), the card snaps back with an inline error.

## Stack

| Concern         | Choice                                  |
|-----------------|-----------------------------------------|
| Framework       | Next.js 15, app router                  |
| Runtime         | React 19 (RSC + server actions)         |
| DB client       | `@supabase/supabase-js`                 |
| Styling         | Tailwind v3 (no CSS-in-JS)              |
| Type discipline | TypeScript strict, no `any`             |
| Fonts           | DM Serif Display / IBM Plex Sans / Mono |
| Palette         | Deep teal · coral · sand                |

Server components are the default. Client components are scoped to
interactive UI (`approval-card.tsx`). Mutations use server actions, not API
routes, so each row maps cleanly to a single typed function call.

The Supabase client is configured to target the `gtm` schema directly
(`db: { schema: "gtm" }`), so the call sites read like
`supabase.from("agent_outputs")` rather than dragging a schema prefix
through every query.

## Run it locally

1. **Spin up Postgres + load folder 01.** Follow
   [`../01-postgres-gtm-schema/README.md`](../01-postgres-gtm-schema/README.md)
   to create the database, apply migrations `001`–`005`, and load
   `seeds/lorefi_seed.sql`. The seed deliberately leaves 5 rows in
   `pending_review` so this UI has something to render the first time you
   open it.

   The schema is plain Postgres, so it works against either Supabase Cloud
   or a local Supabase project — pick whichever fits your demo setup.

2. **Configure env.**

   ```bash
   cd 03-gtm-admin-ui
   cp .env.example .env
   ```

   Fill in:
   - `NEXT_PUBLIC_SUPABASE_URL` — your project's REST URL.
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` — used by RSC reads.
   - `SUPABASE_SERVICE_ROLE_KEY` — used by the approve/reject server
     actions. Never expose this to the browser; the `NEXT_PUBLIC_` prefix
     is deliberately absent.

3. **Install.**

   ```bash
   pnpm install
   ```

4. **Run.**

   ```bash
   pnpm dev
   ```

   Then open [http://localhost:3000](http://localhost:3000). The root
   route redirects to `/gtm-admin/queue`.

## What's intentionally not here

This is a portfolio surface, not a hardened internal tool. The following
were left out as deliberate scope, not gaps:

- **Real authentication.** The reviewer is hardcoded to
  `demo-reviewer@activationlabs.io` in the server actions. In a production
  build this comes from a SSO session and gets stamped into `reviewed_by`,
  with a role gate on `gtm_admin`. The schema is already set up for it —
  `004_agent_queue.sql` grants `ALL` on the table to `gtm_admin` and gates
  everyone else.
- **Role-based filtering of the queue.** A real install would scope
  visibility (e.g. "only show email_ops reviewers their own agent's
  queue"). Here the page shows everything pending.
- **Payload-type-specific renderers.** Every row pretty-prints its
  `payload` JSON. In production each `output_type` would get a renderer:
  the email-ops one would render subject-line variants as a diff against
  the control; the content-ops one would render markdown blog drafts
  inline. The shape of the dispatch (switch on `output_type`) is the easy
  part — the hard part is each renderer, which is product-specific.
- **An audit-log view.** Folder 01 already writes every status transition
  into `gtm.agent_output_audit`. A "history" tab here would be a
  straightforward SELECT against that table, joined back to `agent_outputs`.
- **Bulk actions, filtering, search, pagination.** The pending queue is
  small by design — if it grew large enough to need any of these, the
  agent loop has a different problem.
- **Optimistic counts.** The section counts come from the server fetch
  rather than being live-decremented as cards animate out. A
  `revalidatePath` after each action keeps them honest on the next render
  without the bookkeeping.

## Layout

```
03-gtm-admin-ui/
├── app/
│   ├── globals.css
│   ├── layout.tsx                       -- shell, fonts, demo banner, grid bg
│   ├── page.tsx                         -- root, redirects to /gtm-admin/queue
│   └── gtm-admin/queue/
│       ├── page.tsx                     -- async RSC: fetch + group by agent
│       ├── approval-card.tsx            -- client: optimistic approve/reject UI
│       └── actions.ts                   -- server actions: approveOutput, rejectOutput
├── lib/
│   ├── supabase.ts                      -- typed anon + service clients
│   └── format.ts                        -- relativeTime() with no deps
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── next.config.js
├── .env.example
└── .gitignore
```

## A note on lineage

This is sanitized from a production review-queue surface I built at
**Activation Labs**. The real version reviewed different kinds of agent
outputs against different client schemas; the design — server-rendered
queue read, server-action mutations, row-level guard against concurrent
reviewers, optimistic dismissal with snap-back on failure — is exactly the
shape I'd reach for again. All copy, color, and the Lorefi context are
fictional; the pattern is real.
