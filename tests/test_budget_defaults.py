"""Defaults and uniqueness of a budget plan."""

from budget_helpers import BUDGET_PLANS, create


def test_new_plan_defaults_to_solo_empire_draft_thb(client, owner):
    response = create(client, owner, name="Defaults")
    assert response.status_code == 201, response.text
    plan = response.json()
    assert plan["owner_scope"] == "solo_empire"
    assert plan["status"] == "draft"
    assert plan["currency"] == "THB"
    assert plan["version"] == 1
    assert plan["category"] is None


def test_planned_amount_keeps_its_decimal_value(client, owner):
    plan = create(client, owner, name="Decimal", planned_amount=1234.56).json()
    assert plan["planned_amount"] == 1234.56


def test_two_plans_may_share_a_name_and_period(client, owner):
    first = create(client, owner, name="Groceries", category="food")
    second = create(client, owner, name="Groceries", category="food")
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] != second.json()["id"]


def test_an_import_keeps_the_old_id(client, owner):
    imported = create(client, owner, name="Imported", legacy_id=4242)
    assert imported.status_code == 201, imported.text
    assert imported.json()["id"] == 4242
    assert imported.json()["legacy_id"] == 4242
    found = client.get(f"{BUDGET_PLANS}/legacy/4242", headers=owner)
    assert found.status_code == 200, found.text
    assert found.json()["name"] == "Imported"
    assert create(client, owner, name="Again", legacy_id=4242).status_code == 409
