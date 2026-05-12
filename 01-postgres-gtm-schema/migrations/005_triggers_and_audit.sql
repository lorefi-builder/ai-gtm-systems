-- 005_triggers_and_audit.sql
-- Two pieces of dynamic behavior:
--   1. agent_output_audit: an immutable log of every status change on
--      gtm.agent_outputs, written by trigger.
--   2. advance_lead_funnel: when an activity arrives whose type maps to a
--      funnel transition (mql_qualified, demo_booked, opp_created,
--      closed_won, closed_lost), advance the lead and stamp mql_at / sql_at.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Audit log for agent_outputs status changes
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gtm.agent_output_audit (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  output_id  uuid NOT NULL REFERENCES gtm.agent_outputs(id) ON DELETE CASCADE,
  old_status text,
  new_status text NOT NULL,
  changed_at timestamptz NOT NULL DEFAULT now(),
  changed_by text,
  notes      text
);

COMMENT ON TABLE gtm.agent_output_audit IS
  'Append-only log of every status change on gtm.agent_outputs, including initial insert.';
COMMENT ON COLUMN gtm.agent_output_audit.old_status IS
  'NULL for the row representing the initial insert (pending_review).';

CREATE INDEX IF NOT EXISTS idx_agent_output_audit_output
  ON gtm.agent_output_audit (output_id, changed_at DESC);

CREATE OR REPLACE FUNCTION gtm.log_agent_output_status_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO gtm.agent_output_audit (output_id, old_status, new_status, changed_by, notes)
    VALUES (NEW.id, NULL, NEW.status, NEW.reviewed_by, NEW.review_notes);
    RETURN NEW;
  END IF;

  IF OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO gtm.agent_output_audit (output_id, old_status, new_status, changed_by, notes)
    VALUES (NEW.id, OLD.status, NEW.status, NEW.reviewed_by, NEW.review_notes);
  END IF;

  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION gtm.log_agent_output_status_change IS
  'Writes a row to gtm.agent_output_audit on every INSERT and on UPDATE OF status.';

DROP TRIGGER IF EXISTS trg_agent_outputs_audit_insert ON gtm.agent_outputs;
CREATE TRIGGER trg_agent_outputs_audit_insert
AFTER INSERT ON gtm.agent_outputs
FOR EACH ROW EXECUTE FUNCTION gtm.log_agent_output_status_change();

DROP TRIGGER IF EXISTS trg_agent_outputs_audit_update ON gtm.agent_outputs;
CREATE TRIGGER trg_agent_outputs_audit_update
AFTER UPDATE OF status ON gtm.agent_outputs
FOR EACH ROW EXECUTE FUNCTION gtm.log_agent_output_status_change();

-- Audit table is read-mostly for both roles.
GRANT SELECT ON gtm.agent_output_audit TO gtm_agent;
GRANT ALL    ON gtm.agent_output_audit TO gtm_admin;


-- ---------------------------------------------------------------------------
-- 2. Activity -> funnel state advancement
-- ---------------------------------------------------------------------------
--
-- Mapping (only advances forward; "lost" is terminal and overrides any
-- non-terminal state):
--   mql_qualified -> mql   (sets mql_at if NULL)
--   demo_booked   -> sql   (sets sql_at if NULL)
--   opp_created   -> opp
--   closed_won    -> won
--   closed_lost   -> lost

CREATE OR REPLACE FUNCTION gtm.advance_lead_funnel()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  target_state text;
BEGIN
  target_state := CASE NEW.activity_type
    WHEN 'mql_qualified' THEN 'mql'
    WHEN 'demo_booked'   THEN 'sql'
    WHEN 'opp_created'   THEN 'opp'
    WHEN 'closed_won'    THEN 'won'
    WHEN 'closed_lost'   THEN 'lost'
    ELSE NULL
  END;

  IF target_state IS NULL THEN
    RETURN NEW;
  END IF;

  -- Stamp first-seen mql_at / sql_at independent of state-rank guarding, so
  -- out-of-order event arrivals (e.g. a backfill that inserts closed_won
  -- before the demo_booked it followed) still record the right timestamps.
  IF target_state = 'mql' THEN
    UPDATE gtm.leads
       SET mql_at = LEAST(COALESCE(mql_at, NEW.occurred_at), NEW.occurred_at)
     WHERE id = NEW.lead_id;
  ELSIF target_state = 'sql' THEN
    UPDATE gtm.leads
       SET sql_at = LEAST(COALESCE(sql_at, NEW.occurred_at), NEW.occurred_at)
     WHERE id = NEW.lead_id;
  END IF;

  -- Advance funnel_state only forward; "lost" can override any non-terminal
  -- state.
  UPDATE gtm.leads l
     SET funnel_state = target_state
   WHERE l.id = NEW.lead_id
     AND (
            gtm._funnel_rank(target_state) > gtm._funnel_rank(l.funnel_state)
         OR (target_state = 'lost' AND l.funnel_state NOT IN ('won','lost'))
         );

  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION gtm.advance_lead_funnel IS
  'AFTER INSERT trigger on gtm.activities. Stamps mql_at / sql_at on the '
  'matching activity_types (idempotent: takes the earliest occurred_at seen). '
  'Advances funnel_state forward only — never regresses an already-advanced lead.';

DROP TRIGGER IF EXISTS trg_activities_advance_funnel ON gtm.activities;
CREATE TRIGGER trg_activities_advance_funnel
AFTER INSERT ON gtm.activities
FOR EACH ROW EXECUTE FUNCTION gtm.advance_lead_funnel();

COMMIT;
