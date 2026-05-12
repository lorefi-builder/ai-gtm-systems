-- The exact pattern the email-ops agent in folder 02 uses to identify
-- underperforming subject-line variants. Open-rate is derived from
-- gtm.activities (activity_type = 'email_opened') joined back to
-- gtm.experiment_exposures temporally.
--
-- Thresholds are tuned to the demo seed (5+ exposures, < 0.30 open rate)
-- vs the agent's production defaults (100+, 0.18). Adjust as needed.

with exposures_per_variant as (
  select v.id          as variant_id,
         v.experiment_id,
         v.variant_name,
         v.subject_line,
         e.name        as experiment_name,
         count(distinct x.lead_id) as exposure_count
  from gtm.experiment_variants v
  join gtm.experiments         e on e.id = v.experiment_id
  join gtm.experiment_exposures x on x.variant_id = v.id
  where e.status = 'active'
    and e.primary_metric = 'open_rate'
  group by v.id, v.experiment_id, v.variant_name, v.subject_line, e.name
),
opens_per_variant as (
  select x.variant_id,
         count(distinct x.lead_id) filter (
           where a.activity_type = 'email_opened'
             and a.occurred_at >= x.exposed_at
         ) as open_count
  from gtm.experiment_exposures x
  left join gtm.activities a
    on a.lead_id = x.lead_id
   and a.occurred_at >= x.exposed_at
  group by x.variant_id
),
rates as (
  select e.experiment_id,
         e.experiment_name,
         e.variant_id,
         e.variant_name,
         e.subject_line,
         e.exposure_count,
         coalesce(o.open_count, 0)::numeric / nullif(e.exposure_count, 0) as open_rate
  from exposures_per_variant e
  left join opens_per_variant o on o.variant_id = e.variant_id
)
select *
from rates
where exposure_count >= 5
  and open_rate < 0.30
order by experiment_name, open_rate asc;
