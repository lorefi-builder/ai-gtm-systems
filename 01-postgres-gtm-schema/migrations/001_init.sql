-- 001_init.sql
-- Bootstrap: extensions, schema, roles, and a reusable updated_at trigger.
--
-- Roles:
--   gtm_admin -- application/owner role with full access (operators, services)
--   gtm_agent -- least-privilege role for autonomous agents:
--                INSERT into gtm.agent_outputs (propose), SELECT on lead state.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS gtm;
COMMENT ON SCHEMA gtm IS 'Lorefi GTM data model: leads, activities, experiments, agent proposal queue.';

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'gtm_admin') THEN
    CREATE ROLE gtm_admin NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'gtm_agent') THEN
    CREATE ROLE gtm_agent NOLOGIN;
  END IF;
END
$$;

GRANT USAGE ON SCHEMA gtm TO gtm_admin, gtm_agent;
GRANT CREATE ON SCHEMA gtm TO gtm_admin;

-- Future objects in this schema inherit role grants by default.
ALTER DEFAULT PRIVILEGES IN SCHEMA gtm GRANT ALL ON TABLES TO gtm_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA gtm GRANT ALL ON SEQUENCES TO gtm_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA gtm GRANT EXECUTE ON FUNCTIONS TO gtm_admin;

-- Generic BEFORE UPDATE trigger: stamps updated_at on every modification.
CREATE OR REPLACE FUNCTION gtm.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION gtm.set_updated_at IS
  'Generic BEFORE UPDATE trigger function. Attach to any table with an updated_at column.';

-- Funnel rank helper used by the activity -> funnel_state advancement trigger
-- (defined in 005). Lives here so it is callable from any later migration.
CREATE OR REPLACE FUNCTION gtm._funnel_rank(state text)
RETURNS int
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT CASE state
    WHEN 'anonymous' THEN 0
    WHEN 'known'     THEN 1
    WHEN 'mql'       THEN 2
    WHEN 'sql'       THEN 3
    WHEN 'opp'       THEN 4
    WHEN 'won'       THEN 5
    WHEN 'lost'      THEN 5
    ELSE -1
  END;
$$;

COMMENT ON FUNCTION gtm._funnel_rank IS
  'Ordinal rank of a funnel state. won and lost share rank 5 — both are terminal.';

COMMIT;
