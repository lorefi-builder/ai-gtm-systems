-- 004_agent_queue.sql
-- The "agents propose, humans approve, db enforces" queue.
--
-- Agents INSERT rows in status='pending_review'. Reviewers UPDATE to
-- 'approved' or 'rejected'. An 'approved' output can later be UPDATEd to
-- 'shipped' when it's actually published.
--
-- Enforcement layers, defense in depth:
--   1. CHECK on status values (no rogue states).
--   2. CHECK on field coherence per status (e.g. shipped requires shipped_at).
--   3. Trigger gtm.enforce_agent_output_transition() rejects illegal
--      old->new transitions (CHECK constraints can't see OLD).
--   4. RLS policy restricts gtm_agent to INSERT-as-pending and SELECT.

BEGIN;

CREATE TABLE IF NOT EXISTS gtm.agent_outputs (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_name    text NOT NULL
    CHECK (agent_name IN ('email_ops','content_ops')),
  output_type   text NOT NULL
    CHECK (output_type IN ('subject_line_variant','blog_draft','ad_copy','social_caption')),
  target_ref    text,
  payload       jsonb NOT NULL,
  status        text NOT NULL DEFAULT 'pending_review'
    CHECK (status IN ('pending_review','approved','rejected','shipped')),
  reviewed_at   timestamptz,
  reviewed_by   text,
  review_notes  text,
  shipped_at    timestamptz,
  shipped_ref   text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),

  -- Each status implies a coherent set of populated review/ship columns.
  CONSTRAINT chk_agent_output_status_fields CHECK (
       (status = 'pending_review'
            AND reviewed_at IS NULL
            AND shipped_at  IS NULL)
    OR (status IN ('approved','rejected')
            AND reviewed_at IS NOT NULL
            AND shipped_at  IS NULL)
    OR (status = 'shipped'
            AND reviewed_at IS NOT NULL
            AND shipped_at  IS NOT NULL)
  )
);

COMMENT ON TABLE  gtm.agent_outputs IS
  'Queue of agent-generated content awaiting human review. State machine: '
  'pending_review -> {approved | rejected}; approved -> shipped. '
  'rejected and shipped are terminal.';
COMMENT ON COLUMN gtm.agent_outputs.agent_name IS
  'Which agent proposed this row. Currently: email_ops, content_ops.';
COMMENT ON COLUMN gtm.agent_outputs.output_type IS
  'subject_line_variant | blog_draft | ad_copy | social_caption.';
COMMENT ON COLUMN gtm.agent_outputs.target_ref IS
  'Domain pointer: experiment_id for variant proposals, content topic slug for '
  'blog drafts, channel:campaign for ad copy, etc.';
COMMENT ON COLUMN gtm.agent_outputs.payload IS
  'The actual proposed content. Shape varies by output_type (see seed for examples).';
COMMENT ON COLUMN gtm.agent_outputs.shipped_ref IS
  'External id created when the output was published — e.g. inserted variant id, '
  'CMS post id, ad creative id.';

DROP TRIGGER IF EXISTS trg_agent_outputs_updated_at ON gtm.agent_outputs;
CREATE TRIGGER trg_agent_outputs_updated_at
BEFORE UPDATE ON gtm.agent_outputs
FOR EACH ROW EXECUTE FUNCTION gtm.set_updated_at();

-- The queue UI: SELECT ... WHERE status = 'pending_review' ORDER BY created_at.
CREATE INDEX IF NOT EXISTS idx_agent_outputs_status        ON gtm.agent_outputs (status);
-- Per-agent dashboards / activity feeds.
CREATE INDEX IF NOT EXISTS idx_agent_outputs_agent_created ON gtm.agent_outputs (agent_name, created_at DESC);


-- Transition guard. CHECK constraints cannot reference OLD, so legal-transition
-- enforcement lives in a trigger that fires only when status actually changes.
CREATE OR REPLACE FUNCTION gtm.enforce_agent_output_transition()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    IF NOT (
         (OLD.status = 'pending_review' AND NEW.status IN ('approved','rejected'))
      OR (OLD.status = 'approved'       AND NEW.status =  'shipped')
    ) THEN
      RAISE EXCEPTION
        'invalid agent_outputs status transition: % -> % (allowed: pending_review->approved|rejected, approved->shipped)',
        OLD.status, NEW.status
        USING ERRCODE = 'check_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION gtm.enforce_agent_output_transition IS
  'Rejects illegal status transitions on gtm.agent_outputs. rejected and shipped are terminal.';

DROP TRIGGER IF EXISTS trg_agent_outputs_transition ON gtm.agent_outputs;
CREATE TRIGGER trg_agent_outputs_transition
BEFORE UPDATE OF status ON gtm.agent_outputs
FOR EACH ROW EXECUTE FUNCTION gtm.enforce_agent_output_transition();


-- Grants: agents can propose (INSERT) and read their own backlog. Admins
-- handle review + shipping.
GRANT SELECT, INSERT ON gtm.agent_outputs TO gtm_agent;
GRANT ALL            ON gtm.agent_outputs TO gtm_admin;


-- RLS: agents may only insert rows in the initial state. They cannot update
-- their own proposals to "approve" them.
ALTER TABLE gtm.agent_outputs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_agent_outputs_admin_all      ON gtm.agent_outputs;
CREATE POLICY p_agent_outputs_admin_all      ON gtm.agent_outputs
  FOR ALL    TO gtm_admin USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS p_agent_outputs_agent_select   ON gtm.agent_outputs;
CREATE POLICY p_agent_outputs_agent_select   ON gtm.agent_outputs
  FOR SELECT TO gtm_agent USING (true);

DROP POLICY IF EXISTS p_agent_outputs_agent_insert   ON gtm.agent_outputs;
CREATE POLICY p_agent_outputs_agent_insert   ON gtm.agent_outputs
  FOR INSERT TO gtm_agent WITH CHECK (status = 'pending_review');

COMMIT;
