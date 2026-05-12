{{ config(materialized='view') }}

-- =============================================================================
-- stg_activities — clean + cast pass over raw_lorefi.raw_activities.
-- -----------------------------------------------------------------------------
-- Responsibilities:
--   * Cast occurred_at to timestamp.
--   * Lowercase activity_type so the downstream filters (`where activity_type
--     = 'demo_booked'` in the funnel marts) match regardless of upstream
--     casing drift.
-- =============================================================================

with source as (
    select * from {{ source('raw_lorefi', 'raw_activities') }}
),

renamed as (
    select
        activity_id,
        lead_id,
        lower(trim(activity_type))                                   as activity_type,
        cast(occurred_at as timestamp)                               as occurred_at
    from source
)

select * from renamed
