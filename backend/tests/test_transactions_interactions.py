"""Transaction, campaign, and interaction API tests.

Covers relationships (customer/product/campaign linkage), date filtering,
empty result sets, reference validation, and append-only behavior.
"""

from decimal import Decimal

from fastapi.testclient import TestClient


def _make_customer(auth_client: TestClient, unique: str, tag: str) -> int:
    response = auth_client.post(
        "/api/v1/customers",
        json={
            "first_name": "Test",
            "last_name": tag,
            "email": f"{tag}-{unique}@example.com",
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def _make_product(auth_client: TestClient, unique: str, tag: str) -> int:
    response = auth_client.post(
        "/api/v1/products",
        json={
            "sku": f"SKU-{tag}-{unique}",
            "name": f"Item {tag}",
            "category": "Gadgets",
            "unit_price": "25.00",
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def _make_campaign(auth_client: TestClient, unique: str, tag: str) -> int:
    response = auth_client.post(
        "/api/v1/campaigns",
        json={
            "name": f"Campaign {tag}-{unique}",
            "channel": "email",
            "campaign_type": "promotional",
            "status": "active",
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def test_protected_areas_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/transactions").status_code == 401
    assert client.post("/api/v1/transactions", json={}).status_code == 401
    assert client.get("/api/v1/campaigns").status_code == 401
    assert client.post("/api/v1/campaigns", json={}).status_code == 401
    assert client.get("/api/v1/interactions").status_code == 401
    assert client.post("/api/v1/interactions", json={}).status_code == 401


def test_empty_result_sets(auth_client: TestClient) -> None:
    for path in ("transactions", "interactions"):
        body = auth_client.get(f"/api/v1/{path}", params={"customer_id": 999999}).json()
        assert body == {"items": [], "total": 0, "page": 1, "page_size": 50}


def test_transaction_create_computes_total(auth_client: TestClient, unique: str) -> None:
    customer_id = _make_customer(auth_client, unique, "txn")
    product_id = _make_product(auth_client, unique, "txn")
    response = auth_client.post(
        "/api/v1/transactions",
        json={
            "customer_id": customer_id,
            "product_id": product_id,
            "quantity": 2,
            "unit_price": "25.00",
            "discount": "5.00",
            "status": "completed",
            "transaction_date": "2026-08-01T10:00:00Z",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert Decimal(str(body["total_amount"])) == Decimal("45.00")

    fetched = auth_client.get(f"/api/v1/transactions/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["customer_id"] == customer_id
    assert fetched.json()["product_id"] == product_id


def test_transaction_rejects_dangling_references(auth_client: TestClient, unique: str) -> None:
    customer_id = _make_customer(auth_client, unique, "dangle")
    product_id = _make_product(auth_client, unique, "dangle")
    base = {
        "customer_id": customer_id,
        "product_id": product_id,
        "quantity": 1,
        "unit_price": "10.00",
        "transaction_date": "2026-08-01T10:00:00Z",
    }
    assert (
        auth_client.post("/api/v1/transactions", json={**base, "customer_id": 999999}).status_code
        == 404
    )
    assert (
        auth_client.post("/api/v1/transactions", json={**base, "product_id": 999999}).status_code
        == 404
    )


def test_transaction_rejects_invalid_input(auth_client: TestClient, unique: str) -> None:
    customer_id = _make_customer(auth_client, unique, "badtxn")
    product_id = _make_product(auth_client, unique, "badtxn")
    base = {
        "customer_id": customer_id,
        "product_id": product_id,
        "quantity": 1,
        "unit_price": "10.00",
        "transaction_date": "2026-08-01T10:00:00Z",
    }
    assert auth_client.post("/api/v1/transactions", json={**base, "quantity": 0}).status_code == 422
    assert (
        auth_client.post("/api/v1/transactions", json={**base, "discount": "99.00"}).status_code
        == 422
    )
    assert (
        auth_client.post("/api/v1/transactions", json={**base, "status": "shipped"}).status_code
        == 422
    )
    assert auth_client.get("/api/v1/transactions/999999").status_code == 404


def test_transaction_customer_product_and_date_filters(
    auth_client: TestClient, unique: str
) -> None:
    alice = _make_customer(auth_client, unique, "alice")
    bob = _make_customer(auth_client, unique, "bob")
    product_id = _make_product(auth_client, unique, "dates")

    def buy(customer_id: int, day: str) -> None:
        response = auth_client.post(
            "/api/v1/transactions",
            json={
                "customer_id": customer_id,
                "product_id": product_id,
                "quantity": 1,
                "unit_price": "10.00",
                "transaction_date": f"2026-07-{day}T10:00:00Z",
            },
        )
        assert response.status_code == 201

    buy(alice, "05")
    buy(alice, "20")
    buy(bob, "10")

    only_alice = auth_client.get("/api/v1/transactions", params={"customer_id": alice}).json()
    assert only_alice["total"] == 2
    assert {item["customer_id"] for item in only_alice["items"]} == {alice}

    july_first_half = auth_client.get(
        "/api/v1/transactions",
        params={
            "product_id": product_id,
            "date_from": "2026-07-01T00:00:00Z",
            "date_to": "2026-07-10T23:59:59Z",
        },
    ).json()
    assert july_first_half["total"] == 2

    by_status = auth_client.get(
        "/api/v1/transactions", params={"customer_id": alice, "status": "completed"}
    ).json()
    assert by_status["total"] == 2


def test_campaign_crud_and_validation(auth_client: TestClient, unique: str) -> None:
    created = auth_client.post(
        "/api/v1/campaigns",
        json={
            "name": f"Monsoon Sale-{unique}",
            "channel": "email",
            "campaign_type": "seasonal",
            "status": "draft",
            "start_date": "2026-09-01T00:00:00Z",
            "end_date": "2026-09-30T00:00:00Z",
            "budget": "5000.00",
        },
    )
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    fetched = auth_client.get(f"/api/v1/campaigns/{campaign_id}")
    assert fetched.status_code == 200
    assert Decimal(str(fetched.json()["budget"])) == Decimal("5000.00")

    updated = auth_client.put(f"/api/v1/campaigns/{campaign_id}", json={"status": "active"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "active"

    active = auth_client.get("/api/v1/campaigns", params={"status": "active"}).json()
    assert any(item["id"] == campaign_id for item in active["items"])

    bad_dates = auth_client.post(
        "/api/v1/campaigns",
        json={
            "name": f"Bad-{unique}",
            "channel": "email",
            "campaign_type": "seasonal",
            "start_date": "2026-09-30T00:00:00Z",
            "end_date": "2026-09-01T00:00:00Z",
        },
    )
    assert bad_dates.status_code == 422
    assert auth_client.get("/api/v1/campaigns/999999").status_code == 404


def test_interaction_create_with_campaign_linkage(auth_client: TestClient, unique: str) -> None:
    customer_id = _make_customer(auth_client, unique, "engaged")
    campaign_id = _make_campaign(auth_client, unique, "engage")
    response = auth_client.post(
        "/api/v1/interactions",
        json={
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "interaction_type": "open",
            "channel": "email",
            "occurred_at": "2026-08-15T09:30:00Z",
            "summary": "Opened the sale newsletter",
            "extra": {"device": "mobile"},
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["campaign_id"] == campaign_id
    assert body["extra"] == {"device": "mobile"}


def test_interaction_without_campaign_and_filters(auth_client: TestClient, unique: str) -> None:
    customer_id = _make_customer(auth_client, unique, "organic")
    campaign_id = _make_campaign(auth_client, unique, "organic")
    for payload in (
        {
            "customer_id": customer_id,
            "interaction_type": "visit",
            "channel": "web",
            "occurred_at": "2026-08-10T12:00:00Z",
        },
        {
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "interaction_type": "click",
            "channel": "email",
            "occurred_at": "2026-08-11T12:00:00Z",
        },
    ):
        assert auth_client.post("/api/v1/interactions", json=payload).status_code == 201

    mine = auth_client.get("/api/v1/interactions", params={"customer_id": customer_id}).json()
    assert mine["total"] == 2

    via_campaign = auth_client.get(
        "/api/v1/interactions", params={"campaign_id": campaign_id}
    ).json()
    assert via_campaign["total"] == 1
    assert via_campaign["items"][0]["interaction_type"] == "click"

    by_type = auth_client.get(
        "/api/v1/interactions",
        params={"customer_id": customer_id, "interaction_type": "visit"},
    ).json()
    assert by_type["total"] == 1

    by_date = auth_client.get(
        "/api/v1/interactions",
        params={
            "customer_id": customer_id,
            "date_from": "2026-08-11T00:00:00Z",
            "date_to": "2026-08-11T23:59:59Z",
        },
    ).json()
    assert by_date["total"] == 1


def test_interaction_rejects_dangling_references_and_bad_types(
    auth_client: TestClient, unique: str
) -> None:
    customer_id = _make_customer(auth_client, unique, "lonely")
    base = {
        "customer_id": customer_id,
        "interaction_type": "visit",
        "channel": "web",
        "occurred_at": "2026-08-10T12:00:00Z",
    }
    assert (
        auth_client.post("/api/v1/interactions", json={**base, "customer_id": 999999}).status_code
        == 404
    )
    assert (
        auth_client.post("/api/v1/interactions", json={**base, "campaign_id": 999999}).status_code
        == 404
    )
    assert (
        auth_client.post(
            "/api/v1/interactions", json={**base, "interaction_type": "telepathy"}
        ).status_code
        == 422
    )
    assert auth_client.get("/api/v1/interactions/999999").status_code == 404


def test_transaction_sorting(auth_client: TestClient, unique: str) -> None:
    customer_id = _make_customer(auth_client, unique, "sorter")
    product_id = _make_product(auth_client, unique, "sorter")
    for day, price in (("2026-01-05", "10.00"), ("2026-03-15", "30.00"), ("2026-02-10", "20.00")):
        response = auth_client.post(
            "/api/v1/transactions",
            json={
                "customer_id": customer_id,
                "product_id": product_id,
                "quantity": 1,
                "unit_price": price,
                "transaction_date": f"{day}T10:00:00Z",
            },
        )
        assert response.status_code == 201
    by_amount = auth_client.get(
        "/api/v1/transactions",
        params={"customer_id": customer_id, "sort_by": "total_amount", "order": "desc"},
    ).json()
    assert [item["total_amount"] for item in by_amount["items"]] == ["30.00", "20.00", "10.00"]
    by_date = auth_client.get(
        "/api/v1/transactions",
        params={"customer_id": customer_id, "sort_by": "transaction_date", "order": "asc"},
    ).json()
    assert [item["transaction_date"][:10] for item in by_date["items"]] == [
        "2026-01-05",
        "2026-02-10",
        "2026-03-15",
    ]
