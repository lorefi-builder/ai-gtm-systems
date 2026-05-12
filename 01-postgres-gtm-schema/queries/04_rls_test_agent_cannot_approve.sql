-- Proves the row-level security policy on gtm.agent_outputs:
-- the gtm_agent role can INSERT rows in 'pending_review' but
-- cannot UPDATE existing rows to 'approved' or 'shipped'.
-- The database enforces "agents propose, humans approve."

-- Switch to the agent role
set role gtm_agent;

-- This should fail with permission denied or update 0 rows
update gtm.agent_outputs
set status = 'approved'
where status = 'pending_review';

-- Switch back
reset role;
