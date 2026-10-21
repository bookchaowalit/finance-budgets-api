# Product

<!-- impeccable:product-schema 1 -->

## Platform

api

## Users

- The Solo Empire owner, through `life-dashboard-web` (finance page: active budget plans that cover
  today, with the amount spent taken from `finance-transactions-api`), the cell's own MCP server
  (`budgets-mcp`) and the hosted tool hub (`platform-mcp-remote-worker`).
- Automations with an `empire-platform` token (for example `owner-mcp`), within the permissions
  `budgets.budget-plan:read|write|delete`.

## Product Purpose

The list of planned spending: one budget plan per category and period, with the amount planned,
the owner scope it belongs to and where it stands (draft, active, closed, cancelled). Actual
spending is not stored here; consumers compare a plan to the transactions of the same category
and period.

Success: every budget the owner follows exists once as a plan with a valid period, and the
dashboard can show planned against spent for the current period.

## Positioning

One capability, one service: its own API (Railway), its own database (Neon) with row-level
security per workspace, and authorization, executions and audit through `empire-platform`. It is
workspace-scoped, so the same service can serve other tenants without code changes.

## Operating Context

- Production: `https://budgets-api-production-690e.up.railway.app` (`/health`), deployed by
  merging to `main` after CI.
- Data starts empty (created 2026-10-12 from the retired `finance_*` tables' fields); imports keep
  old ids in `legacy_id`.
- Monitored by `platform-uptime-worker` (probed hourly, because the service sleeps when idle);
  errors go to Sentry without personal data.

## Capabilities and Constraints

- `/v1/budget-plans`: list (filters `owner_scope`, `category`, `status`; ordered by id), stats
  (grouped by one of those filters), get, get-by-legacy-id, create (with `Idempotency-Key`),
  patch (with `expected_version`), delete.
- Rules: `name` (at most 200 characters), `period_start`, `period_end` and `planned_amount` are
  required; `planned_amount` cannot be negative (zero is allowed); `owner_scope` (default
  `solo_empire`) and `status` (default `draft`) are fixed enums; `currency` defaults to THB and
  has at most 12 characters; `period_end` cannot be before `period_start`, on create or on update
  (422 `invalid_value` naming both fields; the same day for both is allowed).
- Plan names are not unique: two plans may share a name, category and period.
- Out of scope: spent amounts and category lists (kept by `finance-transactions-api`), and
  overlap checks between plans of the same category.

## Measures

Proposed (nothing collects them yet):

- Active plans whose period covers today, per owner scope.
- Share of transactions' categories that have an active plan in the current period.
- 5xx rate and p95 latency on `/v1/budget-plans` (Sentry and uptime worker).
