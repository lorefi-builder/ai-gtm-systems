# Quick queries

Sample queries against the `gtm.*` schema. Use these to verify your
local or Supabase install is wired up correctly, or as starter templates
for what the analytics layer in folder 04 builds on.

## Files

| File | Purpose |
|---|---|
| `01_funnel_state_distribution.sql` | How many leads are in each funnel state. The fastest sanity check. |
| `02_agent_queue_as_admin_ui_sees_it.sql` | What `/gtm-admin/queue` from folder 03 would render. |
| `03_agent_output_status_breakdown.sql` | Status distribution across both agents. |
| `04_rls_test_agent_cannot_approve.sql` | Proves the RLS policy: agent role cannot UPDATE rows out of `pending_review`. |
| `05_audit_log_after_approval.sql` | Approve a row, then read the audit trail the trigger wrote. |
| `06_funnel_trigger_test.sql` | Insert an activity, watch the lead's `funnel_state` advance. |
| `07_underperforming_variants.sql` | The exact query the email-ops agent in folder 02 runs. |

## How to use

Paste any one of these into the Supabase SQL Editor (or psql against a
local instance) after running the migrations and seed in
`../migrations/` and `../seeds/`.
