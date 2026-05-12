{{ config(materialized='view') }}

-- =============================================================================
-- stg_leads — clean + cast pass over raw_lorefi.raw_leads.
-- -----------------------------------------------------------------------------
-- Responsibilities:
--   * Lowercase email so joins on email are case-insensitive.
--   * NULL out blank strings on optional columns (source_campaign).
--   * Cast created_at to a true timestamp so downstream date math is safe in
--     both Snowflake and DuckDB.
-- This is a view by config because the source is small and clarity matters
-- more than read performance at this layer.
-- =============================================================================

with source as (
    select * from {{ source('raw_lorefi', 'raw_leads') }}
),

renamed as (
    select
        lead_id,
        lower(email)                                                 as email,
        company,
        product_interest,
        source,
        nullif(trim(source_campaign), '')                            as source_campaign,
        cast(created_at as timestamp)                                as created_at,
        lower(owner_email)                                           as owner_email
    from source
)

select * from renamed
