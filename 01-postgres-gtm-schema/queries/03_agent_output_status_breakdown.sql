-- Distribution of agent outputs by status and agent. Shows that the
-- seed populates all four states (pending_review, approved, rejected,
-- shipped) so the admin UI has things to render in every mode.

select status,
       agent_name,
       count(*) as outputs
from gtm.agent_outputs
group by status, agent_name
order by status, agent_name;
