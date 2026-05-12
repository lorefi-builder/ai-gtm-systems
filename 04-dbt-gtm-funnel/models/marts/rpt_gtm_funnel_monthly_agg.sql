{{ config(materialized='table') }}

-- =============================================================================
-- rpt_gtm_funnel_monthly_agg — monthly funnel tracker by acquisition source.
-- -----------------------------------------------------------------------------
-- Aggregates rpt_gtm_funnel_raw to one row per (month, source). The cohort
-- definition is "leads created in month X" — every count is a stage that
-- those leads eventually reached, regardless of when. This keeps the rates
-- internally consistent (`sqls` is always ≤ `mqls`) without needing
-- pivot-stage gymnastics.
--
-- Portability notes:
--   * DATE_TRUNC('month', ts) works identically on Snowflake and DuckDB.
--   * We compute rates as cast(num as numeric) / nullif(denom, 0). NULLIF
--     gives the SAFE_DIVIDE-style guard (no division by zero) and keeps the
--     SQL portable — neither warehouse has a native SAFE_DIVIDE we can rely
--     on across versions.
-- =============================================================================

with funnel as (
    select * from {{ ref('rpt_gtm_funnel_raw') }}
),

agg as (
    select
        cast(date_trunc('month', created_at) as date)                as month,
        source,
        count(*)                                                      as leads,
        count(case when mql_at is not null         then 1 end)        as mqls,
        count(case when sql_at is not null         then 1 end)        as sqls,
        count(case when opp_created_at is not null then 1 end)        as opps,
        count(case when is_won                     then 1 end)        as won,
        count(case when is_lost                    then 1 end)        as lost,
        avg(case when is_won or is_lost then days_to_close end)       as avg_days_to_close,
        sum(coalesce(net_bookings, 0))                                as total_net_bookings
    from funnel
    group by 1, 2
)

select
    month,
    source,
    leads,
    mqls,
    sqls,
    opps,
    won,
    lost,
    cast(sqls as numeric) / nullif(mqls, 0)                          as mql_to_sql_rate,
    cast(opps as numeric) / nullif(sqls, 0)                          as sql_to_opp_rate,
    cast(won  as numeric) / nullif(opps, 0)                          as opp_to_won_rate,
    avg_days_to_close,
    total_net_bookings
from agg
order by month, source
