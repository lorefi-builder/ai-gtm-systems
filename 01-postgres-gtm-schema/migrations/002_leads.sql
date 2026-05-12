-- 002_leads.sql
-- Leads + activities. Lead funnel state is the source of truth for "where is
-- this account in our motion?" Activities are the append-only log that drives
-- funnel_state forward via the trigger defined in 005.

BEGIN;

CREATE TABLE IF NOT EXISTS gtm.leads (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email            text NOT NULL UNIQUE,
  -- Stored generated column so we can index/aggregate by company domain
  -- without a per-query split_part().
  email_domain     text GENERATED ALWAYS AS (lower(split_part(email, '@', 2))) STORED,
  company          text,
  product_interest text
    CHECK (product_interest IS NULL
           OR product_interest IN ('discover','studio','insights','bundle')),
  funnel_state     text NOT NULL DEFAULT 'anonymous'
    CHECK (funnel_state IN ('anonymous','known','mql','sql','opp','won','lost')),
  mql_at           timestamptz,
  sql_at           timestamptz,
  source           text,
  source_campaign  text,
  owner_email      text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE gtm.leads IS
  'One row per known person/email. funnel_state is monotonic-forward except that lost is terminal.';
COMMENT ON COLUMN gtm.leads.product_interest IS
  'Lorefi product the lead engaged with: discover | studio | insights | bundle.';
COMMENT ON COLUMN gtm.leads.funnel_state IS
  'Current funnel position. Advanced by trigger on gtm.activities INSERT (see 005).';
COMMENT ON COLUMN gtm.leads.source IS
  'Top-level acquisition channel — organic_search, paid_search, webinar, conference, etc.';
COMMENT ON COLUMN gtm.leads.source_campaign IS
  'Specific campaign/asset within the source. Free-form but conventionally <channel>:<slug>.';

DROP TRIGGER IF EXISTS trg_leads_updated_at ON gtm.leads;
CREATE TRIGGER trg_leads_updated_at
BEFORE UPDATE ON gtm.leads
FOR EACH ROW EXECUTE FUNCTION gtm.set_updated_at();

CREATE INDEX IF NOT EXISTS idx_leads_funnel_state ON gtm.leads (funnel_state);
CREATE INDEX IF NOT EXISTS idx_leads_source       ON gtm.leads (source);
CREATE INDEX IF NOT EXISTS idx_leads_email_domain ON gtm.leads (email_domain);
CREATE INDEX IF NOT EXISTS idx_leads_owner_email  ON gtm.leads (owner_email);


CREATE TABLE IF NOT EXISTS gtm.activities (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id       uuid NOT NULL REFERENCES gtm.leads(id) ON DELETE CASCADE,
  activity_type text NOT NULL,
  occurred_at   timestamptz NOT NULL DEFAULT now(),
  payload       jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE gtm.activities IS
  'Append-only event log per lead. Drives funnel_state via trigger in 005.';
COMMENT ON COLUMN gtm.activities.activity_type IS
  'Examples: page_view, signup, doc_download, nurture_open, nurture_click, mql_qualified, '
  'demo_booked, demo_attended, opp_created, closed_won, closed_lost, trial_started.';
COMMENT ON COLUMN gtm.activities.payload IS
  'Activity-specific attributes (path, score, slot, amount, etc.). Schema is intentionally flexible.';

DROP TRIGGER IF EXISTS trg_activities_updated_at ON gtm.activities;
CREATE TRIGGER trg_activities_updated_at
BEFORE UPDATE ON gtm.activities
FOR EACH ROW EXECUTE FUNCTION gtm.set_updated_at();

CREATE INDEX IF NOT EXISTS idx_activities_lead_id     ON gtm.activities (lead_id);
CREATE INDEX IF NOT EXISTS idx_activities_occurred_at ON gtm.activities (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_activities_type        ON gtm.activities (activity_type);


-- Role grants
GRANT SELECT ON gtm.leads, gtm.activities TO gtm_agent;
GRANT ALL    ON gtm.leads, gtm.activities TO gtm_admin;


-- Row-level security: gtm_agent is read-only, gtm_admin has full access.
ALTER TABLE gtm.leads      ENABLE ROW LEVEL SECURITY;
ALTER TABLE gtm.activities ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_leads_admin_all     ON gtm.leads;
CREATE POLICY p_leads_admin_all     ON gtm.leads
  FOR ALL    TO gtm_admin USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS p_leads_agent_select  ON gtm.leads;
CREATE POLICY p_leads_agent_select  ON gtm.leads
  FOR SELECT TO gtm_agent USING (true);

DROP POLICY IF EXISTS p_activities_admin_all    ON gtm.activities;
CREATE POLICY p_activities_admin_all    ON gtm.activities
  FOR ALL    TO gtm_admin USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS p_activities_agent_select ON gtm.activities;
CREATE POLICY p_activities_agent_select ON gtm.activities
  FOR SELECT TO gtm_agent USING (true);

COMMIT;
