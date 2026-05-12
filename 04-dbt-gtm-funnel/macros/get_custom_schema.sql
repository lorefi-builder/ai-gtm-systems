-- =============================================================================
-- generate_schema_name override
-- -----------------------------------------------------------------------------
-- dbt's default behavior concatenates the target schema with any custom schema
-- configured on a model (e.g. `dev_staging`, `dev_marts`). For a portfolio
-- project we want clean schema names (`staging`, `marts`, `raw`) regardless of
-- which target you're running. This override yields:
--
--     +schema not set         →  target.schema     (e.g. "main")
--     +schema: staging        →  "staging"
--     +schema: marts          →  "marts"
--
-- In a real multi-environment setup you would usually keep dbt's default so
-- dev and prod schemas don't collide — overriding it like this is a deliberate
-- choice for a single-developer demo.
-- =============================================================================

{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
