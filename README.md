# finance-budgets-api
The Budgets cell: its own API (Railway, serverless) and its own Neon
database, first generated from `cell.yaml` (one of the ten finance
services split on 2026-10-12). It
reuses empire-platform for identity, authorization, executions and audit over
HTTP with the caller's token.

| | |
|---|---|
| API | Railway project `finance-budgets-api`, service `budgets-api` (Serverless) |
| Data | Neon project `finance-budgets-api`, database `budgets` |
| Registry | solo-empire `repository-catalog/registries/online-systems.yaml` (`budgets`) |

## API

Every resource has list, stats, get, get-by-legacy-id, create, patch and delete
(see `cellkit/app.py`). Permissions are `budgets.<resource>:read|write|delete`.

| Path | Resource | Filters |
|---|---|---|
| `/v1/budget-plans` | budget-plan | `owner_scope`, `category`, `status` |

## Develop and operate

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/pytest -q
NEON_API_KEY=... .venv/bin/budgets-db provision
npm install && railway config apply && railway up --ci --service budgets-api
railway scale --service budgets-api asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0   # next to Neon and the platform
```

Railway variables: `SENTRY_DSN` (error reporting; unset = off, see `src/cellkit/_sentry.py`),
`BUDGETS_DB_MODE=hosted`, `BUDGETS_DB_URL_API`,
`BUDGETS_JWT_PUBLIC_KEY_PEM`, `BUDGETS_JWT_ISSUER`, `EMPIRE_PLATFORM_URL`.
