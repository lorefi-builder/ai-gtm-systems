{{ config(materialized='table') }}

-- =============================================================================
-- rpt_gtm_funnel_raw — record-level funnel report.
-- -----------------------------------------------------------------------------
-- One row per lead. For each, surfaces the timestamp at which they reached
-- every funnel stage and how long they took to get there. This is the lowest
-- grain of the GTM funnel — rpt_gtm_funnel_monthly_agg rolls up from it.
--
-- Funnel stages and how each timestamp is derived:
--
--   anonymous       Conceptual only — no stg_leads row yet. Not represented
--                   in this report.
--   known           Lead row exists in stg_leads. `created_at` is always set;
--                   the report's grain is one row per known lead.
--   mql_at          Earliest content_download or email_opened activity. Those
--                   two events are the first self-served engagement signals
--                   past an anonymous page view, so we use the first of them
--                   as the MQL stamp. NULL when neither has happened.
--   sql_at          Earliest demo_booked activity. Booking time on a sales
--                   call is the canonical SQL signal at Lorefi.
--   opp_created_at  COALESCE of the opp_created activity (if present) and
--                   raw_opportunities.created_at (always present once the
--                   opp exists). The activity stream may lag the OLTP table
--                   in real loads, so the opps table is the more reliable
--                   source.
--   closed_at       COALESCE of closed_won/closed_lost activity and
--                   raw_opportunities.close_date.
--
--   is_won / is_lost  True when *either* the corresponding close activity
--                     exists OR the opp's stage is closed_won/closed_lost.
--                     Defensive against missing events in either source.
--
--   last_stage      The furthest stage actually reached. A single CASE
--                   walks won/lost → opp → sql → mql → known.
--
--   net_bookings    Sum of int_fact_opps_by_line_items.net_bookings across
--                   the lead's opportunities. NULL if no opp.
-- =============================================================================

with leads as (
    select * from {{ ref('int_fact_leads_with_activities') }}
),

activities as (
    select * from {{ ref('stg_activities') }}
),

mql_events as (
    select
        lead_id,
        min(occurred_at) as mql_at
    from activities
    where activity_type in ('content_download', 'email_opened')
    group by 1
),

sql_events as (
    select
        lead_id,
        min(occurred_at) as sql_at
    from activities
    where activity_type = 'demo_booked'
    group by 1
),

opp_events as (
    select
        lead_id,
        min(occurred_at) as opp_event_at
    from activities
    where activity_type = 'opp_created'
    group by 1
),

close_events as (
    select
        lead_id,
        min(occurred_at) as close_event_at,
        max(case when activity_type = 'closed_won'  then 1 else 0 end) as has_won_event,
        max(case when activity_type = 'closed_lost' then 1 else 0 end) as has_lost_event
    from activities
    where activity_type in ('closed_won', 'closed_lost')
    group by 1
),

opps_rolled as (
    select
        lead_id,
        min(created_at) as opp_first_created_at,
        max(close_date) as opp_close_date,
        max(case when stage = 'closed_won'  then 1 else 0 end) as opp_won_flag,
        max(case when stage = 'closed_lost' then 1 else 0 end) as opp_lost_flag,
        sum(net_bookings) as net_bookings
    from {{ ref('int_fact_opps_by_line_items') }}
    group by 1
),

joined as (
    select
        l.lead_id,
        l.email,
        l.company,
        l.product_interest,
        l.source,
        l.source_campaign,
        l.created_at,
        m.mql_at,
        s.sql_at,
        coalesce(o.opp_event_at, opp.opp_first_created_at)              as opp_created_at,
        coalesce(c.close_event_at, cast(opp.opp_close_date as timestamp)) as closed_at,
        case
            when coalesce(c.has_won_event, 0) = 1
              or coalesce(opp.opp_won_flag, 0) = 1
            then true else false
        end                                                              as is_won,
        case
            when coalesce(c.has_lost_event, 0) = 1
              or coalesce(opp.opp_lost_flag, 0) = 1
            then true else false
        end                                                              as is_lost,
        opp.net_bookings
    from leads l
    left join mql_events    m   on m.lead_id   = l.lead_id
    left join sql_events    s   on s.lead_id   = l.lead_id
    left join opp_events    o   on o.lead_id   = l.lead_id
    left join close_events  c   on c.lead_id   = l.lead_id
    left join opps_rolled   opp on opp.lead_id = l.lead_id
),

final as (
    select
        lead_id,
        email,
        company,
        product_interest,
        source,
        source_campaign,
        created_at,
        mql_at,
        sql_at,
        opp_created_at,
        closed_at,
        case
            when is_won                       then 'won'
            when is_lost                      then 'lost'
            when opp_created_at is not null   then 'opp'
            when sql_at is not null           then 'sql'
            when mql_at is not null           then 'mql'
            else                                   'known'
        end as last_stage,
        is_won,
        is_lost,
        case when mql_at is not null
            then cast(mql_at as date) - cast(created_at as date)
        end as days_to_mql,
        case when sql_at is not null
            then cast(sql_at as date) - cast(created_at as date)
        end as days_to_sql,
        case when closed_at is not null
            then cast(closed_at as date) - cast(created_at as date)
        end as days_to_close,
        net_bookings
    from joined
)

select * from final
