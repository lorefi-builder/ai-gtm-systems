{{ config(materialized='view') }}

-- =============================================================================
-- stg_opportunities — clean + cast pass over raw_lorefi.raw_opportunities.
-- -----------------------------------------------------------------------------
-- Responsibilities:
--   * Cast amount to a real numeric and close_date to a date.
--   * Normalize stage casing to lowercase so the accepted_values test in
--     models/schema.yml has a stable surface to match against.
--   * Preserve `product_lines` as the raw comma-separated string — the
--     intermediate layer (int_fact_opps_by_line_items) is what splits it
--     into one row per product.
-- =============================================================================

with source as (
    select * from {{ source('raw_lorefi', 'raw_opportunities') }}
),

renamed as (
    select
        opp_id,
        lead_id,
        account_id,
        lower(trim(stage))                                           as stage,
        cast(amount as numeric(12, 2))                               as amount,
        cast(close_date as date)                                     as close_date,
        product_lines,
        cast(seat_count as integer)                                  as seat_count,
        cast(created_at as timestamp)                                as created_at
    from source
)

select * from renamed
