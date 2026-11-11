-- SPEC-003 (2026-11-11): exact money, ISO 4217 currency, workspace-defined scope (budgets).
-- Amounts move from double precision to numeric; currency codes must be three upper-case letters;
-- owner_scope (the owner's own life areas) becomes scope, a free label each workspace defines.
-- Append-only: do not edit once applied.

-- budget-plan
ALTER TABLE budgets.budget_plans NO FORCE ROW LEVEL SECURITY;
UPDATE budgets.budget_plans SET currency = upper(btrim(currency));
ALTER TABLE budgets.budget_plans FORCE ROW LEVEL SECURITY;
ALTER TABLE budgets.budget_plans RENAME COLUMN owner_scope TO scope;
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'budgets.budget_plans'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'budgets.budget_plans'::regclass AND attname = 'scope')] LOOP EXECUTE format('ALTER TABLE budgets.budget_plans DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE budgets.budget_plans ALTER COLUMN scope SET DEFAULT '';
ALTER TABLE budgets.budget_plans ADD CONSTRAINT budget_plans_scope_check CHECK (length(scope) <= 64);
DO $$ DECLARE i text; BEGIN SELECT indexname INTO i FROM pg_indexes WHERE schemaname = 'budgets' AND tablename = 'budget_plans' AND indexdef LIKE '%(workspace_id, scope)'; IF i IS NOT NULL THEN EXECUTE format('ALTER INDEX budgets.%I RENAME TO budget_plans_scope', i); END IF; END $$;
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'budgets.budget_plans'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'budgets.budget_plans'::regclass AND attname = 'planned_amount')] LOOP EXECUTE format('ALTER TABLE budgets.budget_plans DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE budgets.budget_plans ALTER COLUMN planned_amount TYPE numeric(19,4) USING planned_amount::numeric(19,4);
ALTER TABLE budgets.budget_plans ADD CONSTRAINT budget_plans_planned_amount_check CHECK (planned_amount >= 0);
DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE conrelid = 'budgets.budget_plans'::regclass AND contype = 'c' AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'budgets.budget_plans'::regclass AND attname = 'currency')] LOOP EXECUTE format('ALTER TABLE budgets.budget_plans DROP CONSTRAINT %I', c); END LOOP; END $$;
ALTER TABLE budgets.budget_plans ADD CONSTRAINT budget_plans_currency_check CHECK (currency ~ '^[A-Z]{3}$');
