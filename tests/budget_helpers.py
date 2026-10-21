"""Shared helpers for the budgets domain tests."""

from typing import Any

BUDGET_PLANS = "/v1/budget-plans"


def create(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {
        "name": "Plan",
        "period_start": "2026-11-01",
        "period_end": "2026-11-30",
        "planned_amount": 1000,
        **fields,
    }
    return client.post(BUDGET_PLANS, headers=owner, json=body)
