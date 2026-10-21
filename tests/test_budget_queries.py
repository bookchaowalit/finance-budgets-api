"""Listing, grouping and the lifecycle of a budget plan."""

from budget_helpers import BUDGET_PLANS, create


def test_list_filters_by_category(client, owner):
    create(client, owner, name="Food Q4", category="food-filter")
    create(client, owner, name="Travel Q4", category="travel-filter")
    listed = client.get(BUDGET_PLANS, headers=owner, params={"category": "food-filter"})
    assert listed.status_code == 200, listed.text
    names = {item["name"] for item in listed.json()["items"]}
    assert names == {"Food Q4"}


def test_list_filters_by_status_and_scope(client, owner):
    create(client, owner, name="Live venture", status="active", owner_scope="venture")
    create(client, owner, name="Draft venture", owner_scope="venture")
    listed = client.get(
        BUDGET_PLANS,
        headers=owner,
        params={"status": "active", "owner_scope": "venture"},
    )
    assert listed.status_code == 200, listed.text
    assert [item["name"] for item in listed.json()["items"]] == ["Live venture"]


def test_list_filter_with_an_unknown_status_is_refused(client, owner):
    listed = client.get(BUDGET_PLANS, headers=owner, params={"status": "frozen"})
    assert listed.status_code == 422


def test_list_refuses_a_field_that_is_not_a_filter(client, owner):
    listed = client.get(BUDGET_PLANS, headers=owner, params={"name": "x"})
    assert listed.status_code == 422


def test_plans_are_listed_in_creation_order(client, owner):
    ids = [create(client, owner, name=f"Order {n}").json()["id"] for n in range(3)]
    listed = client.get(BUDGET_PLANS, headers=owner).json()["items"]
    assert [item["id"] for item in listed] == sorted(ids)


def test_stats_count_plans_per_status(client, owner):
    create(client, owner, name="Draft one")
    create(client, owner, name="Active one", status="active")
    stats = client.get(
        f"{BUDGET_PLANS}/stats", headers=owner, params={"group_by": "status"}
    )
    assert stats.status_code == 200, stats.text
    groups = stats.json()["groups"]
    assert groups["draft"] >= 1
    assert groups["active"] >= 1


def test_stats_count_plans_per_category(client, owner):
    create(client, owner, name="Rent", category="housing-stats")
    stats = client.get(
        f"{BUDGET_PLANS}/stats", headers=owner, params={"group_by": "category"}
    )
    assert stats.status_code == 200, stats.text
    assert stats.json()["groups"]["housing-stats"] == 1


def test_stats_refuse_a_field_that_is_not_a_filter(client, owner):
    stats = client.get(
        f"{BUDGET_PLANS}/stats", headers=owner, params={"group_by": "planned_amount"}
    )
    assert stats.status_code == 422


def test_activating_a_plan_bumps_its_version(client, owner):
    plan = create(client, owner, name="Activate me").json()
    activated = client.patch(
        f"{BUDGET_PLANS}/{plan['id']}", headers=owner, json={"status": "active"}
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "active"
    assert activated.json()["version"] == 2


def test_a_patch_that_changes_nothing_keeps_the_version(client, owner):
    plan = create(client, owner, name="Stable", planned_amount=50).json()
    same = client.patch(
        f"{BUDGET_PLANS}/{plan['id']}",
        headers=owner,
        json={"name": "Stable", "planned_amount": 50},
    )
    assert same.status_code == 200, same.text
    assert same.json()["version"] == 1


def test_a_stale_expected_version_is_refused(client, owner):
    plan = create(client, owner, name="Versioned").json()
    path = f"{BUDGET_PLANS}/{plan['id']}"
    assert client.patch(path, headers=owner, json={"notes": "a"}).status_code == 200
    stale = client.patch(
        path, headers=owner, json={"notes": "b", "expected_version": 1}
    )
    assert stale.status_code == 409


def test_a_plan_cannot_be_given_a_negative_amount_on_update(client, owner):
    plan = create(client, owner, name="Keep amount", planned_amount=75).json()
    path = f"{BUDGET_PLANS}/{plan['id']}"
    refused = client.patch(path, headers=owner, json={"planned_amount": -5})
    assert refused.status_code == 422
    assert client.get(path, headers=owner).json()["planned_amount"] == 75


def test_a_required_field_cannot_be_cleared(client, owner):
    plan = create(client, owner, name="Needs dates").json()
    refused = client.patch(
        f"{BUDGET_PLANS}/{plan['id']}", headers=owner, json={"period_start": None}
    )
    assert refused.status_code == 422


def test_deleting_a_plan_removes_it(client, owner):
    plan = create(client, owner, name="Short lived").json()
    path = f"{BUDGET_PLANS}/{plan['id']}"
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
    assert client.delete(path, headers=owner).status_code == 404
