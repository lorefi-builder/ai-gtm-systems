-- Demonstrates the funnel-advancement trigger from migration 005.
-- Insert a demo_booked activity and watch the lead's funnel_state
-- automatically advance to 'sql' with sql_at populated.

-- 1. Pick an MQL who has not yet been promoted to SQL
with target_lead as (
  select id, email, funnel_state, mql_at, sql_at
  from gtm.leads
  where funnel_state = 'mql'
  order by created_at asc
  limit 1
)
select * from target_lead;

-- 2. Copy the lead id from above, then run this with that id substituted:
-- insert into gtm.activities (lead_id, activity_type, occurred_at, payload)
-- values ('<paste-lead-id-here>', 'demo_booked', now(), '{}'::jsonb);

-- 3. Re-check the lead — funnel_state should now be 'sql' and sql_at populated
-- select id, email, funnel_state, mql_at, sql_at
-- from gtm.leads
-- where id = '<paste-lead-id-here>';
