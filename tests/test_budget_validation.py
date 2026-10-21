"""What budgets refuses: missing fields, unknown kinds, negative amounts, backwards periods."""

from budget_helpers import BUDGET_PLANS, create


def test_name_is_required(client, owner):
    response = client.post(
        BUDGET_PLANS,
        headers=owner,
        json={
            "period_start": "2026-11-01",
            "period_end": "2026-11-30",
            "planned_amount": 10,
        },
    )
    assert response.status_code == 422


def test_name_is_limited_to_200_characters(client, owner):
    assert create(client, owner, name="x" * 201).status_code == 422
    assert create(client, owner, name="y" * 200).status_code == 201


def test_period_start_is_required(client, owner):
    response = client.post(
        BUDGET_PLANS,
        headers=owner,
        json={"name": "No start", "period_end": "2026-11-30", "planned_amount": 10},
    )
    assert response.status_code == 422


def test_period_end_is_required(client, owner):
    response = client.post(
        BUDGET_PLANS,
        headers=owner,
        json={"name": "No end", "period_start": "2026-11-01", "planned_amount": 10},
    )
    assert response.status_code == 422


def test_planned_amount_is_required(client, owner):
    response = client.post(
        BUDGET_PLANS,
        headers=owner,
        json={
            "name": "No amount",
            "period_start": "2026-11-01",
            "period_end": "2026-11-30",
        },
    )
    assert response.status_code == 422


def test_planned_amount_cannot_be_negative(client, owner):
    assert create(client, owner, name="Negative", planned_amount=-1).status_code == 422
    assert create(client, owner, name="Zero", planned_amount=0).status_code == 201


def test_a_date_must_be_a_real_calendar_date(client, owner):
    response = create(client, owner, name="Bad date", period_start="2026-02-30")
    assert response.status_code == 422


def test_owner_scope_must_be_a_known_scope(client, owner):
    response = create(client, owner, name="Odd scope", owner_scope="family")
    assert response.status_code == 422


def test_status_must_be_a_known_status(client, owner):
    response = create(client, owner, name="Odd status", status="frozen")
    assert response.status_code == 422


def test_currency_code_is_at_most_12_characters(client, owner):
    assert create(client, owner, name="Long ccy", currency="C" * 13).status_code == 422
    assert create(client, owner, name="USD plan", currency="USD").status_code == 201


def test_unknown_fields_are_refused(client, owner):
    response = create(client, owner, name="Extra", colour="red")
    assert response.status_code == 422


def test_a_budget_period_cannot_end_before_it_starts(client, owner):
    backwards = create(
        client,
        owner,
        name="Backwards",
        period_start="2026-12-01",
        period_end="2026-11-30",
    )
    assert backwards.status_code == 422, backwards.text
    assert backwards.json()["detail"] == {
        "error": "invalid_value",
        "fields": ["period_end", "period_start"],
    }
    one_day = create(
        client,
        owner,
        name="One day",
        period_start="2026-12-01",
        period_end="2026-12-01",
    )
    assert one_day.status_code == 201, one_day.text


def test_moving_the_end_before_the_start_is_refused_on_update(client, owner):
    plan = create(client, owner, name="November", period_start="2026-11-01").json()
    path = f"{BUDGET_PLANS}/{plan['id']}"
    refused = client.patch(path, headers=owner, json={"period_end": "2026-10-31"})
    assert refused.status_code == 422, refused.text
    unchanged = client.get(path, headers=owner).json()
    assert unchanged["period_end"] == "2026-11-30"
    assert unchanged["version"] == 1
    # A patch that touches neither date still works.
    renamed = client.patch(path, headers=owner, json={"name": "Renamed"})
    assert renamed.status_code == 200, renamed.text
