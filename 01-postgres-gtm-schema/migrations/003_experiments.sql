-- 003_experiments.sql
-- Experimentation tables. Lightweight A/B framework: an experiment has
-- 2+ variants, leads get exposed to one variant, downstream activities
-- close the loop on the primary metric.

BEGIN;

CREATE TABLE IF NOT EXISTS gtm.experiments (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name           text NOT NULL UNIQUE,
  hypothesis     text,
  primary_metric text NOT NULL,
  started_at     timestamptz,
  ended_at       timestamptz,
  status         text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','paused','completed','archived')),
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  CHECK (ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at)
);

COMMENT ON COLUMN gtm.experiments.primary_metric IS
  'The single metric this experiment is powered to move (e.g. reply_rate, demo_request_rate).';

DROP TRIGGER IF EXISTS trg_experiments_updated_at ON gtm.experiments;
CREATE TRIGGER trg_experiments_updated_at
BEFORE UPDATE ON gtm.experiments
FOR EACH ROW EXECUTE FUNCTION gtm.set_updated_at();


CREATE TABLE IF NOT EXISTS gtm.experiment_variants (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_id uuid NOT NULL REFERENCES gtm.experiments(id) ON DELETE CASCADE,
  variant_name  text NOT NULL,
  traffic_pct   numeric(5,2) NOT NULL
    CHECK (traffic_pct >= 0 AND traffic_pct <= 100),
  is_control    boolean NOT NULL DEFAULT false,
  subject_line  text,
  body_template text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (experiment_id, variant_name)
);

COMMENT ON COLUMN gtm.experiment_variants.traffic_pct IS
  'Share of exposures routed to this variant. Variants within an experiment should sum to 100.';
COMMENT ON COLUMN gtm.experiment_variants.subject_line IS
  'Email-experiment variants only: the subject line under test.';
COMMENT ON COLUMN gtm.experiment_variants.body_template IS
  'Email-experiment variants only: the body template with {{token}} placeholders.';

-- At most one control per experiment.
CREATE UNIQUE INDEX IF NOT EXISTS uq_variants_one_control_per_experiment
  ON gtm.experiment_variants (experiment_id) WHERE is_control;

CREATE INDEX IF NOT EXISTS idx_variants_experiment_id
  ON gtm.experiment_variants (experiment_id);

DROP TRIGGER IF EXISTS trg_variants_updated_at ON gtm.experiment_variants;
CREATE TRIGGER trg_variants_updated_at
BEFORE UPDATE ON gtm.experiment_variants
FOR EACH ROW EXECUTE FUNCTION gtm.set_updated_at();


CREATE TABLE IF NOT EXISTS gtm.experiment_exposures (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  variant_id uuid NOT NULL REFERENCES gtm.experiment_variants(id) ON DELETE CASCADE,
  lead_id    uuid NOT NULL REFERENCES gtm.leads(id)               ON DELETE CASCADE,
  exposed_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  -- A lead is exposed to a given variant at most once.
  UNIQUE (variant_id, lead_id)
);

COMMENT ON TABLE gtm.experiment_exposures IS
  'Records that a lead saw a specific variant. Join through to activities to compute metrics.';

DROP TRIGGER IF EXISTS trg_exposures_updated_at ON gtm.experiment_exposures;
CREATE TRIGGER trg_exposures_updated_at
BEFORE UPDATE ON gtm.experiment_exposures
FOR EACH ROW EXECUTE FUNCTION gtm.set_updated_at();

CREATE INDEX IF NOT EXISTS idx_exposures_lead_id    ON gtm.experiment_exposures (lead_id);
CREATE INDEX IF NOT EXISTS idx_exposures_variant_id ON gtm.experiment_exposures (variant_id);
CREATE INDEX IF NOT EXISTS idx_exposures_exposed_at ON gtm.experiment_exposures (exposed_at DESC);


-- Role grants: agents can read the experiment design so they can propose
-- variants. Only admins mutate experiment definitions.
GRANT SELECT ON gtm.experiments, gtm.experiment_variants, gtm.experiment_exposures TO gtm_agent;
GRANT ALL    ON gtm.experiments, gtm.experiment_variants, gtm.experiment_exposures TO gtm_admin;

COMMIT;
