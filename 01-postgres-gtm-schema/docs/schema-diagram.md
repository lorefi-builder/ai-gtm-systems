# Schema diagram — `gtm`

ASCII ERD for the Lorefi GTM schema. Boxes are tables, arrows point from the
foreign-key column to the referenced primary key. `1 ───< N` means "one to
many" (one parent row, many child rows).

```
                ┌──────────────────────────────────┐
                │ gtm.leads                        │
                ├──────────────────────────────────┤
                │ id              uuid PK          │
                │ email           text UQ          │
                │ email_domain    text GEN STORED  │
                │ company         text             │
                │ product_interest text            │
                │ funnel_state    text  ◄ trigger  │   (advanced by 005)
                │ mql_at          timestamptz      │
                │ sql_at          timestamptz      │
                │ source          text             │
                │ source_campaign text             │
                │ owner_email     text             │
                │ created_at / updated_at          │
                └────┬────────────────────────┬────┘
                  1  │                      1 │
                     │                        │
                  N  ▼                      N ▼
   ┌──────────────────────────┐   ┌──────────────────────────────┐
   │ gtm.activities           │   │ gtm.experiment_exposures     │
   ├──────────────────────────┤   ├──────────────────────────────┤
   │ id            uuid PK    │   │ id          uuid PK          │
   │ lead_id       uuid FK ──►│   │ lead_id     uuid FK ─────────┘
   │ activity_type text       │   │ variant_id  uuid FK ─────────┐
   │ occurred_at   timestamptz│   │ exposed_at  timestamptz      │
   │ payload       jsonb      │   │ created_at / updated_at      │
   │ created_at / updated_at  │   │ UNIQUE (variant_id, lead_id) │
   └────────────┬─────────────┘   └──────────────────────────────┘
                │                                                │
                │ AFTER INSERT trigger:                          │
                │   activity_type in                             │
                │   (mql_qualified, demo_booked, opp_created,    │
                │    closed_won, closed_lost)                    │
                │   → advance lead.funnel_state forward          │
                ▼                                                │
        (updates gtm.leads)                                      │
                                                                 ▼
                          ┌──────────────────────────────┐
                          │ gtm.experiment_variants      │
                          ├──────────────────────────────┤
              ┌───────────┤ id            uuid PK        │
              │           │ experiment_id uuid FK ──┐    │
              │           │ variant_name  text      │    │
              │           │ traffic_pct   numeric   │    │
              │           │ is_control    bool      │    │
              │           │ subject_line  text      │    │
              │           │ body_template text      │    │
              │           └─────────────────────────┼────┘
              │                                     │
              │                                     │ N
              │                                     ▼
              │                          ┌──────────────────────────┐
              │                          │ gtm.experiments          │
              │                          ├──────────────────────────┤
              │                          │ id            uuid PK    │
              │                          │ name          text UQ    │
              │                          │ hypothesis    text       │
              │                          │ primary_metric text      │
              │                          │ started_at / ended_at    │
              │                          │ status        text       │
              │                          │ created_at / updated_at  │
              │                          └──────────────────────────┘
              │ 1
              ▼ N (via experiment_exposures, see above)


   ┌──────────────────────────────────┐        ┌──────────────────────────────┐
   │ gtm.agent_outputs                │  1     │ gtm.agent_output_audit       │
   ├──────────────────────────────────┤        ├──────────────────────────────┤
   │ id            uuid PK            │◄────── │ id          uuid PK          │
   │ agent_name    text               │      N │ output_id   uuid FK          │
   │ output_type   text               │        │ old_status  text             │
   │ target_ref    text               │        │ new_status  text             │
   │ payload       jsonb              │        │ changed_at  timestamptz      │
   │ status        text  ◄ state mach │        │ changed_by  text             │
   │ reviewed_at / reviewed_by        │        │ notes       text             │
   │ review_notes                     │        └──────────────────────────────┘
   │ shipped_at  / shipped_ref        │
   │ created_at  / updated_at         │
   └──────────────────────────────────┘
                  ▲
                  │ AFTER INSERT / AFTER UPDATE OF status
                  │ writes one row per state change
                  │ (NULL → pending_review on insert)
                  └──────────────────────────────────────► gtm.agent_output_audit
```

## `agent_outputs.status` state machine

```
                        ┌──────────────────┐
              INSERT ──►│  pending_review  │
                        └────────┬─────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  ▼                             ▼
            ┌──────────┐                  ┌──────────┐
            │ rejected │ (terminal)       │ approved │
            └──────────┘                  └────┬─────┘
                                               │
                                               ▼
                                         ┌──────────┐
                                         │ shipped  │ (terminal)
                                         └──────────┘
```

Enforcement:

- `CHECK (status IN ('pending_review','approved','rejected','shipped'))`
- `CHECK` on coherence of `reviewed_at` / `shipped_at` per status
- `BEFORE UPDATE OF status` trigger `gtm.enforce_agent_output_transition`
  rejects any other old → new transition

## `leads.funnel_state` advancement

```
   anonymous ──► known ──► mql ──► sql ──► opp ──► won
                                                 └──► lost  (terminal)
```

Triggered by `gtm.activities` INSERT:

| activity_type   | target state | side-effect          |
|-----------------|--------------|----------------------|
| `mql_qualified` | `mql`        | sets `mql_at`        |
| `demo_booked`   | `sql`        | sets `sql_at`        |
| `opp_created`   | `opp`        |                      |
| `closed_won`    | `won`        |                      |
| `closed_lost`   | `lost`       | overrides any non-terminal state |

The trigger never regresses a lead — if it is already further along, the
incoming activity is logged but `funnel_state` is unchanged.
