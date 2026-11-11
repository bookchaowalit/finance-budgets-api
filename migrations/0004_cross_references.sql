-- SPEC-006 (2026-11-11): cross-service references between the finance cells (budgets).
-- Append-only: do not edit once applied.

-- The relay sends a record's events in insert order (the row lock makes it the commit order).
ALTER TABLE budgets.outbox ADD COLUMN seq bigint GENERATED ALWAYS AS IDENTITY;
DROP INDEX budgets.outbox_unrelayed;
CREATE INDEX outbox_unrelayed ON budgets.outbox (seq) WHERE relayed_at IS NULL;

-- SPEC-006: cross-service references, fed by finance.events.v1.
CREATE TABLE budgets.ref_targets (
    workspace_id   uuid NOT NULL,
    target         text NOT NULL,
    record_id      bigint NOT NULL,
    status         text,
    deleted        boolean NOT NULL DEFAULT false,
    record_version bigint NOT NULL DEFAULT 0,
    event_seq      bigint NOT NULL DEFAULT 0,
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, target, record_id)
);
CREATE TABLE budgets.ref_sources (
    workspace_id    uuid NOT NULL,
    source          text NOT NULL,
    source_id       bigint NOT NULL,
    field           text NOT NULL,
    target_resource text NOT NULL,
    target_id       bigint,
    deleted         boolean NOT NULL DEFAULT false,
    record_version  bigint NOT NULL DEFAULT 0,
    event_seq       bigint NOT NULL DEFAULT 0,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, source, source_id, field)
);
CREATE INDEX ref_sources_live ON budgets.ref_sources (workspace_id, target_resource, target_id) WHERE NOT deleted;
CREATE TABLE budgets.ref_offsets (
    topic       text NOT NULL,
    partition   integer NOT NULL,
    next_offset bigint NOT NULL,
    PRIMARY KEY (topic, partition)
);
ALTER TABLE budgets.ref_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets.ref_targets FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation ON budgets.ref_targets USING (workspace_id = budgets.current_workspace());
CREATE POLICY publisher_sync ON budgets.ref_targets TO budgets_publisher USING (true) WITH CHECK (true);
GRANT SELECT ON budgets.ref_targets TO budgets_api;
GRANT SELECT, INSERT, UPDATE ON budgets.ref_targets TO budgets_publisher;
ALTER TABLE budgets.ref_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets.ref_sources FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation ON budgets.ref_sources USING (workspace_id = budgets.current_workspace());
CREATE POLICY publisher_sync ON budgets.ref_sources TO budgets_publisher USING (true) WITH CHECK (true);
GRANT SELECT ON budgets.ref_sources TO budgets_api;
GRANT SELECT, INSERT, UPDATE ON budgets.ref_sources TO budgets_publisher;
GRANT SELECT, INSERT, UPDATE ON budgets.ref_offsets TO budgets_publisher;

-- Rows written before SPEC-005 announce themselves once, so other cells learn their ids.
ALTER TABLE budgets.outbox NO FORCE ROW LEVEL SECURITY;
ALTER TABLE budgets.budget_plans NO FORCE ROW LEVEL SECURITY;
INSERT INTO budgets.outbox (workspace_id, type, subject, classification, payload, correlation_id) SELECT workspace_id, 'budgets.budget-plan.snapshot', 'empire:budgets:budget-plan:' || id, 'confidential', jsonb_build_object('scope', scope, 'period_start', period_start, 'period_end', period_end, 'currency', currency, 'status', status, 'version', version, 'deleted', false), 'spec-006-snapshot' FROM budgets.budget_plans ORDER BY id;
ALTER TABLE budgets.budget_plans FORCE ROW LEVEL SECURITY;
ALTER TABLE budgets.outbox FORCE ROW LEVEL SECURITY;
