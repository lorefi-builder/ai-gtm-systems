{{ config(materialized='table') }}

-- =============================================================================
-- int_fact_leads_with_activities — lead dimension enriched with touch metrics.
-- -----------------------------------------------------------------------------
-- For each lead, joins stg_leads to stg_activities and decorates the row with:
--   * first_activity_at / first_activity_type   — earliest touch
--   * last_activity_at  / last_activity_type    — most recent touch
--   * total_activities                          — touch count
--
-- The CTE chain (with_lead_cte → with_first_touch → with_last_touch → final)
-- mirrors the spec convention so each enrichment step is independently
-- readable in a diff. We use row_number() instead of min()/max() because we
-- need to pull the activity_type alongside the timestamp.
-- =============================================================================

with with_lead_cte as (
    select * from {{ ref('stg_leads') }}
),

ranked_activities as (
    select
        lead_id,
        activity_type,
        occurred_at,
        row_number() over (partition by lead_id order by occurred_at asc)  as touch_rank_asc,
        row_number() over (partition by lead_id order by occurred_at desc) as touch_rank_desc
    from {{ ref('stg_activities') }}
),

first_touch as (
    select
        lead_id,
        occurred_at   as first_activity_at,
        activity_type as first_activity_type
    from ranked_activities
    where touch_rank_asc = 1
),

last_touch as (
    select
        lead_id,
        occurred_at   as last_activity_at,
        activity_type as last_activity_type
    from ranked_activities
    where touch_rank_desc = 1
),

activity_counts as (
    select
        lead_id,
        count(*) as total_activities
    from {{ ref('stg_activities') }}
    group by 1
),

with_first_touch as (
    select
        l.lead_id,
        l.email,
        l.company,
        l.product_interest,
        l.source,
        l.source_campaign,
        l.created_at,
        l.owner_email,
        ft.first_activity_at,
        ft.first_activity_type
    from with_lead_cte l
    left join first_touch ft on ft.lead_id = l.lead_id
),

with_last_touch as (
    select
        wft.*,
        lt.last_activity_at,
        lt.last_activity_type,
        coalesce(ac.total_activities, 0) as total_activities
    from with_first_touch wft
    left join last_touch lt on lt.lead_id = wft.lead_id
    left join activity_counts ac on ac.lead_id = wft.lead_id
),

final as (
    select * from with_last_touch
)

select * from final
