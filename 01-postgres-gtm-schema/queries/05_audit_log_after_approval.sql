-- Approve one pending output, then read the audit trail the trigger wrote.
-- Demonstrates the gtm.agent_output_audit table is being populated
-- automatically on every status change.

-- 1. Approve one row
update gtm.agent_outputs
set status = 'approved',
    reviewed_at = now(),
    reviewed_by = 'demo-reviewer@activationlabs.io'
where status = 'pending_review'
order by created_at asc
limit 1
returning id, agent_name, output_type, status;

-- 2. Read the most recent audit entries
select id,
       output_id,
       old_status,
       new_status,
       changed_at,
       changed_by
from gtm.agent_output_audit
order by changed_at desc
limit 5;
