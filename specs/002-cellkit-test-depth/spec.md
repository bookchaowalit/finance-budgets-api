# SPEC-002 — cellkit test depth: characterization tests for the framework copy

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Follows SPEC-001 (coverage ratchet convention). Audit 2026-11-05 proposed raising tests on the 18 thin APIs.

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-002 / 1.0 |
| Status | approved (2026-11-05, see Approval) |
| Repository / path | bookchaowalit/finance-budgets-api / `specs/002-cellkit-test-depth/spec.md` |
| Owner (maker) | Claude Code (implementer session, 2026-11-05) |
| Reviewer (checker) | none separate; gates run by the implementer (ruff, mypy, pytest twice, CI coverage gate) |
| Approver | owner, in chat 2026-11-05 ("ทำต่อเลย") |
| Main-only | yes: committed straight to `main` locally; not pushed |
| Created / approved | 2026-11-05 / 2026-11-05 |

## 1. Problem and intent

- **Problem:** `src/cellkit` (the service's framework copy, shared byte-for-byte with the other finance services) had no tests for the importer, the MCP adapter, the entry points, the SQL generator, and most of the platform client and outbox publisher. Total coverage was 59.05% (815 of 1990 statements missed).
- **Outcome:** characterization tests for those modules, written against a small self-contained spec, with no change under `src/`. Total coverage 92.56%; CI gate ratcheted from 56 to 90.
- **Why now:** the 2026-11-05 audit flagged thin test depth; the same `src/cellkit` is copied into nine sibling repositories, so the tests should travel with it.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| `tests/test_cellkit_*.py` (7 files), `tests/cellkit_support.py`, `tests/cellkit_fixture/cell.yaml`, the CI `coverage-threshold` ratchet, this spec | Any change under `src/`; domain tests; migrations; endpoints; copying the tests into the sibling repositories (a later step); fixing the bug found (pinned as xfail) |

## 3. Behaviour — characterization tests

No behaviour changes. Each file pins what the code already does.

| Test file | Characterizes | Level |
|---|---|---|
| `test_cellkit_sqlgen.py` (10) | Column, table and migration SQL; roles SQL is rerunnable; PostgreSQL enforces checks, uniques, FKs and row-level security per workspace | integration (throwaway PostgreSQL) |
| `test_cellkit_importer.py` (24) | SQLite-to-API conversion, parents-first ordering, cycles in a second pass, rerun counts, dry run, `verify` pagination; the https/loopback rule; the token is never printed | unit (`MockTransport`, tmp SQLite) |
| `test_cellkit_mcp.py` (52) | Config checks (https/loopback, client file, token file, automation token), strict argument models, tool calls and their HTTP mapping, status words without upstream text, read-only mode, entry point | unit (in-process tools, `MockTransport`) |
| `test_cellkit_platform.py` (31) | https/loopback rule; decide, begin, finish, publish; refusals; redirects not followed; fail-closed; token never in errors | unit (`MockTransport`) |
| `test_cellkit_publisher.py` (8) | Outbox sweep per workspace, envelope, batch limit, backoff (capped at 600 s), one Sentry report per sweep, retry clears the error | integration (throwaway PostgreSQL) |
| `test_cellkit_server.py` (16) | `<cell>-api` wiring and refusals (hosted dev issuer, JWKS https), `<cell>-publish` exit codes, `<cell>-db` migrate and provision | unit (uvicorn, `create_app`, `migrate`, `provision` patched) |
| `test_cellkit_db.py` (28) | Names and paths; hosted URLs from the owner-only file; migration guards (edited, empty, new); Neon HTTP and provisioning with the HTTP and psycopg calls faked | unit + integration |

Shared fixtures: `tests/cellkit_support.py` builds the mini cell and a throwaway PostgreSQL on its own port (the harness keeps 5434). The mini cell (`tests/cellkit_fixture/cell.yaml`) has two resources, a ref between them, a self-ref, enums, defaults, unique, json, bool, date range, timestamp and legacy values. No test reads this cell's `cell.yaml`, schema or resources.

### Bug found (pinned, not fixed)

- `test_a_refusal_with_a_non_json_body_is_still_a_denial` is `xfail(strict=True)`. `HttpPlatform.begin` parses a 403 body as JSON; a non-JSON refusal (for example an HTML page from a gateway) raises `JSONDecodeError`. The API maps only `Denied` and `PlatformUnavailable`, so the client gets a 500 instead of a refusal. No write happens either way.

## 4. Interfaces and data

| Interface | Change | Contract |
|---|---|---|
| `src/cellkit/**`, cell API, `cell.yaml` | none | — |
| `.github/workflows/ci.yml` | `coverage-threshold` 56 → 90 | ratchet: measured 92.56% on 2026-11-05, threshold = measured − 2, rounded down |

## 5. Non-functional requirements

| NFR | Target | How it is tested |
|---|---|---|
| Security / privacy | https or loopback only; tokens never printed or put in errors; RLS isolates workspaces | `test_cellkit_importer.py`, `test_cellkit_mcp.py`, `test_cellkit_platform.py`, `test_cellkit_server.py`, `test_cellkit_sqlgen.py` |
| Reliability | outbox retries with capped backoff; a failed sweep reports once | `test_cellkit_publisher.py` |
| Performance | N/A — no hot-path change | — |

## 6. Test plan (characterization, no red run)

- **Red run: none.** These tests pin behaviour that already exists, so they passed on the first run (the ADR-0004 exception for characterization tests, as in SPEC-001). The only failing-by-design test is the strict xfail above.
- **Test levels:** unit tests with `httpx.MockTransport`, monkeypatched Neon HTTP and psycopg, and a tmp SQLite file; integration tests against a throwaway PostgreSQL (pgserver) started per session. No hosted database, platform or network.
- **Coverage (`coverage run --source=src`, 1990 statements):**

| Module | Before | After |
|---|---|---|
| `importer.py` | 0% | 99.32% |
| `mcp.py` | 0% | 100% |
| `server.py` | 0% | 100% |
| `sqlgen.py` | 0% | 100% |
| `platform.py` | 35% | 100% |
| `publisher.py` | 35% | 100% |
| `db.py` | 52% | 99.52% |
| **TOTAL** | **59.05%** | **92.56%** (148 missed) |

- **Not covered, on purpose:** `importer.py` line 255 (`if __name__ == "__main__"`); `db.py` line 305 (`raise SystemExit("neon project stayed locked")`) is unreachable, because the 423 retry loop raises on its last attempt. Reported as dead code; no `src/` change in this spec.
- **Verification run on 2026-11-05:** `uvx ruff@0.17.1 check .` passed; `uvx ruff@0.17.1 format --check .` passed (36 files); `.venv/bin/mypy` passed (30 source files); `.venv/bin/pytest -q --cov` run twice: 220 passed, 4 skipped, 1 xfailed each time (168 new passing tests, 1 new xfail).

## 7. Risks and open questions

| # | Risk or question | Impact | Owner | Resolution / date |
|---|---|---|---|---|
| 1 | Platform or gateway 403 with a non-JSON body returns 500 | client sees a server error instead of a refusal; no write | owner | fix in `src/cellkit/platform.py` in a separate change; the xfail then turns into a pass and must be unmarked |
| 2 | Sibling repositories need `tests/cellkit_support.py` and `tests/cellkit_fixture/` with the test files | copy without them fails on import | owner | copy the three together when rolling out |
| 3 | Dead branch in `db.py` `_neon` | none at runtime | owner | remove in a future `src` change |

## 8. Change log

| Version | Date | Change | Scenarios affected | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-11-05 | Characterization tests for cellkit importer, mcp, server, sqlgen, platform, publisher, db; CI ratchet 56 → 90 | all (no behaviour change) | owner, chat 2026-11-05 |

## Approval

| Gate | Role | Name / date | Decision | Evidence |
|---|---|---|---|---|
| Approved to implement | Approver | Owner, chat 2026-11-05 ("ทำต่อเลย") | approved | audit proposal: raise tests on the 18 thin APIs |
| Checker | none separate | — | not run | gates listed in section 6 |
