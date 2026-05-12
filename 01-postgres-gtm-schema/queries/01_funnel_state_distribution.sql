-- How many leads are in each funnel state.
-- Fastest sanity check that the schema + seed are loaded correctly.

select funnel_state,
       count(*) as leads
from gtm.leads
group by funnel_state
order by case funnel_state
           when 'anonymous' then 0
           when 'known' then 1
           when 'mql' then 2
           when 'sql' then 3
           when 'opp' then 4
           when 'won' then 5
           when 'lost' then 6
         end;
