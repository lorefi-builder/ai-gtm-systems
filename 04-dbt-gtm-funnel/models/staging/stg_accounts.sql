{{ config(materialized='view') }}

-- =============================================================================
-- stg_accounts — clean pass over raw_lorefi.raw_accounts.
-- -----------------------------------------------------------------------------
-- Responsibilities:
--   * Coalesce primary_domain from the raw column, falling back to extracting
--     the domain from primary_email when the column is NULL. We use
--     SPLIT_PART (1-indexed, available in both Snowflake and DuckDB) rather
--     than REGEXP_EXTRACT so the SQL is portable.
--   * Lowercase the resulting domain for case-insensitive joins.
--   * Normalize segment + tier casing.
-- =============================================================================

with source as (
    select * from {{ source('raw_lorefi', 'raw_accounts') }}
),

renamed as (
    select
        account_id,
        account_name,
        lower(
            coalesce(
                nullif(trim(primary_domain), ''),
                split_part(primary_email, '@', 2)
            )
        )                                                            as primary_domain,
        lower(primary_email)                                         as primary_email,
        lower(trim(segment))                                         as segment,
        lower(trim(tier))                                            as tier
    from source
)

select * from renamed
