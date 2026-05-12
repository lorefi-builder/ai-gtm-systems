{% snapshot snp_opp_state %}

{#-
    snp_opp_state — SCD2 history of opportunity state.
    -----------------------------------------------------------------------
    Captures every change to an opportunity's stage, amount, or close_date
    and writes a versioned row with dbt_valid_from / dbt_valid_to. This is
    what lets us answer "what was Lattice Newsroom's opp on Jan 15th?"
    months after the fact — the live stg_opportunities table only ever
    reflects the current state.

    Strategy is 'check' (not 'timestamp') because the source table doesn't
    have a reliable updated_at column we can trust; dbt hashes the
    check_cols on each snapshot run and writes a new version when the
    hash changes.

    In a real Lorefi install this snapshot would run nightly. Pair with
    snapshots-on-staging if you also want SCD2 on lead funnel_state.
-#}

{{
    config(
        target_schema='snapshots',
        unique_key='opp_id',
        strategy='check',
        check_cols=['stage', 'amount', 'close_date']
    )
}}

select
    opp_id,
    lead_id,
    account_id,
    stage,
    amount,
    close_date,
    seat_count,
    product_lines,
    created_at
from {{ ref('stg_opportunities') }}

{% endsnapshot %}
