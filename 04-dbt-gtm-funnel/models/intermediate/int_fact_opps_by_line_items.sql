{{ config(materialized='table') }}

-- =============================================================================
-- int_fact_opps_by_line_items — fan opportunities out to product-line grain.
-- -----------------------------------------------------------------------------
-- Lorefi sells three products that can ship in any combination on a single
-- opportunity. Per-seat list prices (annual):
--
--     Discover  $4,000 / seat   — cross-media search + discovery surface
--     Studio    $4,500 / seat   — editorial workflow + content measurement
--     Insights  $3,000 / seat   — audience analytics + executive reporting
--
-- raw_opportunities stores the product mix as a comma-separated string
-- (e.g. "Discover,Studio,Insights"). This model fans that out into one row
-- per (opp_id, product_line), allocates seats evenly across listed products,
-- and computes a per-line `net_bookings` at list price.
--
-- The split is implemented as three guarded UNION ALL branches rather than
-- a SPLIT_TO_TABLE / UNNEST so the SQL is identical on Snowflake and DuckDB.
-- Because Lorefi only sells three SKUs, the explicit branches double as a
-- contract: if a fourth product ships, this model has to be touched.
--
-- The difference between SUM(net_bookings) OVER (PARTITION BY opp_id) and
-- opp.amount represents the effective bundle / discount applied at the deal
-- level — we surface both so analysts can compare list value vs booked value.
-- =============================================================================

with opps as (
    select * from {{ ref('stg_opportunities') }}
),

opps_with_count as (
    select
        *,
        -- portable comma-counter: works in both Snowflake and DuckDB
        length(product_lines) - length(replace(product_lines, ',', '')) + 1
            as num_product_lines
    from opps
),

discover_lines as (
    select
        opp_id, lead_id, account_id, stage, amount, close_date, created_at,
        seat_count, num_product_lines,
        cast('Discover' as varchar) as product_line,
        cast(4000.00 as numeric(12, 2)) as price_per_seat
    from opps_with_count
    where product_lines like '%Discover%'
),

studio_lines as (
    select
        opp_id, lead_id, account_id, stage, amount, close_date, created_at,
        seat_count, num_product_lines,
        cast('Studio' as varchar) as product_line,
        cast(4500.00 as numeric(12, 2)) as price_per_seat
    from opps_with_count
    where product_lines like '%Studio%'
),

insights_lines as (
    select
        opp_id, lead_id, account_id, stage, amount, close_date, created_at,
        seat_count, num_product_lines,
        cast('Insights' as varchar) as product_line,
        cast(3000.00 as numeric(12, 2)) as price_per_seat
    from opps_with_count
    where product_lines like '%Insights%'
),

unioned as (
    select * from discover_lines
    union all
    select * from studio_lines
    union all
    select * from insights_lines
),

with_allocations as (
    select
        opp_id,
        lead_id,
        account_id,
        product_line,
        stage,
        amount       as opp_amount,
        close_date,
        created_at,
        seat_count   as opp_seat_count,
        num_product_lines,
        -- even seat split — seeds are designed so seat_count is divisible by
        -- num_product_lines. cast to numeric so the division does not floor
        -- on DuckDB's integer-division semantics.
        cast(seat_count as numeric) / num_product_lines              as line_seats,
        price_per_seat,
        (cast(seat_count as numeric) / num_product_lines) * price_per_seat
                                                                     as net_bookings
    from unioned
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['opp_id', 'product_line']) }} as opp_line_id,
        opp_id,
        lead_id,
        account_id,
        product_line,
        stage,
        opp_amount,
        close_date,
        created_at,
        opp_seat_count,
        num_product_lines,
        line_seats,
        price_per_seat,
        net_bookings,
        sum(net_bookings) over (partition by opp_id) as opp_total_net_bookings
    from with_allocations
)

select * from final
