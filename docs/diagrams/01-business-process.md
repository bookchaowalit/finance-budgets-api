# 01 — Business process (As-Is / To-Be)

finance-budgets-api (cell `budgets`) เก็บแผนงบประมาณ (budget plan) ต่อหมวดและช่วงเวลา พร้อมยอดที่วางแผนไว้ ให้ owner ใช้ผ่าน `life-dashboard-web`, `finance-api` และ MCP; ยอดใช้จริงไม่ได้เก็บที่นี่ แต่ผู้เรียกเทียบกับ `finance-transactions-api` เอง

Last reviewed: 2026-11-27 · commit `5e1f83c`

## As-Is (จากโค้ดวันนี้)

```mermaid
flowchart LR
  DASH["life-dashboard-web (หน้า finance)"] --> API
  BFF["finance-api (views, export, erase)"] --> API
  MCP["budgets-mcp / platform-mcp-remote-worker"] --> API
  API["budgets-api (Railway serverless)<br/>/v1/budget-plans"] --> AUTH{"Bearer JWT ผ่าน?"}
  AUTH -->|no| E401["401 unauthenticated"]
  AUTH -->|yes| PDP["empire-platform /v1/authz/decide<br/>budgets.budget-plan:read/write/delete"]
  PDP -->|"deny / platform ล่ม"| E403["403 deny / 503 authorization_unavailable"]
  PDP -->|read| READ["list (limit 1-1000), stats, get, get-by-legacy-id"]
  PDP -->|"create / patch / delete / erase"| TX["transaction เดียว: ตรวจกฎ, เขียน budget_plans + outbox 1 แถวต่อ record"]
  TX -->|ผิดกฎ| E422["422 invalid_value / 428 version_required / 409 conflict"]
  READ --> DB[("Neon budgets: budget_plans, create_keys, outbox<br/>RLS ต่อ workspace")]
  TX --> DB
  TX --> EXEC["empire-platform /v1/executions<br/>begin ก่อน commit, finish หลัง commit (row hash)"]
  EXEC --> INLINE["inline relay หลังเขียน (background, best effort)"]
  JOB["platform-jobs-worker 36 * * * * UTC<br/>GitHub Actions relay-outbox.yml"] --> RELAY["budgets-relay (publisher role, ทุก workspace, retry backoff)"]
  DB --> RELAY
  INLINE --> KAFKA[["Kafka finance.events.v1<br/>เฉพาะ graph fields"]]
  RELAY --> KAFKA
  RELAY --> HB["heartbeat finance-relay-budgets<br/>(relay fail หรือ backlog เกิน 3 ชม.)"]
  KAFKA --> SINK["data-lake-pipelines event-sink → Bronze"]
```

Sources: `cell.yaml`, `pyproject.toml` (platform-cellkit v1.1.1: `cellkit/app.py`, `cellkit/relay.py`, `cellkit/gateway.py`), `migrations/0001_budgets.sql`–`0004_cross_references.sql`, `.github/workflows/relay-outbox.yml`, `.railway/railway.ts`, `README.md`, `PRODUCT.md`

ข้อเท็จจริงสำคัญจากโค้ด:

- โค้ดของ cell มีแค่ `cell.yaml`; route, auth, outbox และ relay มาจาก platform-cellkit v1.1.1 (`src/solo_budgets/` ว่าง)
- กฎ: `name` (ไม่เกิน 200 ตัว), `period_start`, `period_end`, `planned_amount` บังคับ; `planned_amount` เป็น `money` ติดลบไม่ได้; `period_end` ต้องไม่ก่อน `period_start` (422 `invalid_value`); `currency` ISO 4217 ค่าเริ่มต้น THB; PATCH ที่ส่งฟิลด์เงินต้องมี `expected_version` (428, SPEC-009)
- event `budgets.budget-plan.created/updated/deleted` มีเฉพาะ `scope`, `period_start`, `period_end`, `currency`, `status` (ไม่มียอดเงิน ชื่อ หรือ notes)
- cell นี้ไม่มี `references` / `referenced_by`: ไม่ได้อ่าน Kafka กลับมา ลบได้โดยไม่ต้องตรวจ cell อื่น
- `POST /v1/budget-plans/erase` ต้องมี `confirm` = workspace ของผู้เรียก ลบทีละ 1-500 แถว (ค่าเริ่มต้น 200; SPEC-008)
- การตรวจ `X-Gateway-Assertion` (off/report/enforce) และ inline relay ขึ้นกับตัวแปรบน Railway [ต้องยืนยัน: ค่าใน production]

## To-Be (จาก `PRODUCT.md` §Measures และ `specs/004-identity-issuer-trust/spec.md`)

- `specs/004-identity-issuer-trust/spec.md`: cell เชื่อ token ของ platform-identity เคียงข้าง empire-platform; โค้ดอยู่ใน kit แล้ว แต่ "production activation needs a separate owner go"
- `PRODUCT.md` §Measures (Proposed, ยังไม่มีอะไรเก็บ): แผน active ที่ครอบวันนี้ต่อ scope, สัดส่วนหมวดของ transaction ที่มีแผน active ในงวดปัจจุบัน, 5xx และ p95 latency ของ `/v1/budget-plans`
- `PRODUCT.md` §Capabilities: out of scope = ยอดใช้จริง, รายการหมวด และการตรวจแผนซ้อนกัน

## Gap

| ID | As-Is → To-Be | Status | Owner | Evidence |
|---|---|---|---|---|
| G1 | รับ token ของ platform-identity ได้ในโค้ด แต่ยังไม่ยืนยันว่าเปิดใน production → owner ตัดสินเปิดใช้ (ตั้ง `BUDGETS_JWT_IDENTITY_*`) | decide | owner | `specs/004-identity-issuer-trust/spec.md` (Status) |
| G2 | ไม่มีอะไรเก็บ Measures ที่เสนอไว้ → เก็บและรายงานตาม `PRODUCT.md` | decide | owner | `PRODUCT.md` §Measures ("Proposed (nothing collects them yet)") |

## Open questions

- โหมด gateway assertion และ signed events (`BUDGETS_EVENT_SIGNATURES`) ใน production เป็นค่าใด
