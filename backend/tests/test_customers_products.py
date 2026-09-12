"""Customer and product API tests: auth, CRUD, validation, filters, pagination."""

from decimal import Decimal

from fastapi.testclient import TestClient


def _customer_payload(unique: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "first_name": "Asha",
        "last_name": f"Buyer-{unique}",
        "email": f"asha-{unique}@example.com",
        "phone": "+91-9000000001",
        "city": "Mumbai",
        "country": "India",
    }
    payload.update(overrides)
    return payload


def _product_payload(unique: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "sku": f"SKU-{unique}",
        "name": f"Widget-{unique}",
        "category": "Gadgets",
        "brand": "Acme",
        "unit_price": "49.99",
        "currency": "USD",
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def test_customers_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/customers").status_code == 401
    assert client.post("/api/v1/customers", json={}).status_code == 401
    assert client.get("/api/v1/customers/1").status_code == 401


def test_products_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/products").status_code == 401
    assert client.post("/api/v1/products", json={}).status_code == 401


def test_customer_create_and_get_roundtrip(auth_client: TestClient, unique: str) -> None:
    created = auth_client.post("/api/v1/customers", json=_customer_payload(unique))
    assert created.status_code == 201
    body = created.json()
    assert body["id"]
    assert body["email"] == f"asha-{unique}@example.com"
    assert body["created_at"]

    fetched = auth_client.get(f"/api/v1/customers/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_customer_email_is_normalized(auth_client: TestClient, unique: str) -> None:
    created = auth_client.post(
        "/api/v1/customers",
        json=_customer_payload(unique, email=f"MiXeD-{unique}@Example.COM"),
    )
    assert created.status_code == 201
    assert created.json()["email"] == f"mixed-{unique}@example.com"


def test_customer_rejects_invalid_input(auth_client: TestClient, unique: str) -> None:
    bad_email = auth_client.post(
        "/api/v1/customers", json=_customer_payload(unique, email="not-an-email")
    )
    assert bad_email.status_code == 422
    missing_name = auth_client.post(
        "/api/v1/customers", json=_customer_payload(unique, first_name="")
    )
    assert missing_name.status_code == 422


def test_customer_not_found(auth_client: TestClient) -> None:
    assert auth_client.get("/api/v1/customers/999999").status_code == 404
    assert auth_client.put("/api/v1/customers/999999", json={"city": "Goa"}).status_code == 404


def test_customer_update(auth_client: TestClient, unique: str) -> None:
    created = auth_client.post("/api/v1/customers", json=_customer_payload(unique))
    customer_id = created.json()["id"]
    updated = auth_client.put(
        f"/api/v1/customers/{customer_id}", json={"city": "Bengaluru", "phone": None}
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == "Bengaluru"
    assert updated.json()["last_name"] == f"Buyer-{unique}"


def test_customer_search_and_location_filters(auth_client: TestClient, unique: str) -> None:
    auth_client.post("/api/v1/customers", json=_customer_payload(unique, city="Mumbai"))
    auth_client.post(
        "/api/v1/customers",
        json=_customer_payload(f"{unique}-b", first_name="Ravi", last_name="Sharma", city="Delhi"),
    )
    marker = f"Buyer-{unique}"
    by_search = auth_client.get("/api/v1/customers", params={"search": marker})
    assert by_search.json()["total"] == 1
    by_city = auth_client.get("/api/v1/customers", params={"search": unique, "city": "Delhi"})
    assert by_city.json()["total"] == 1
    assert by_city.json()["items"][0]["city"] == "Delhi"


def test_customer_pagination_envelope(auth_client: TestClient, unique: str) -> None:
    for i in range(5):
        auth_client.post(
            "/api/v1/customers",
            json=_customer_payload(f"{unique}-p{i}", email=f"page-{unique}-p{i}@example.com"),
        )
    first = auth_client.get(
        "/api/v1/customers", params={"search": unique, "page": 1, "page_size": 2}
    ).json()
    assert first["total"] == 5
    assert first["page"] == 1
    assert first["page_size"] == 2
    assert len(first["items"]) == 2
    third = auth_client.get(
        "/api/v1/customers", params={"search": unique, "page": 3, "page_size": 2}
    ).json()
    assert len(third["items"]) == 1


def test_product_create_get_and_duplicate_sku(auth_client: TestClient, unique: str) -> None:
    created = auth_client.post("/api/v1/products", json=_product_payload(unique))
    assert created.status_code == 201
    body = created.json()
    assert Decimal(str(body["unit_price"])) == Decimal("49.99")

    fetched = auth_client.get(f"/api/v1/products/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["sku"] == f"SKU-{unique}"

    duplicate = auth_client.post("/api/v1/products", json=_product_payload(unique))
    assert duplicate.status_code == 409


def test_product_rejects_invalid_input(auth_client: TestClient, unique: str) -> None:
    negative_price = auth_client.post(
        "/api/v1/products", json=_product_payload(unique, unit_price="-1")
    )
    assert negative_price.status_code == 422
    assert auth_client.get("/api/v1/products/999999").status_code == 404


def test_product_category_and_active_filters(auth_client: TestClient, unique: str) -> None:
    auth_client.post("/api/v1/products", json=_product_payload(f"{unique}-a"))
    auth_client.post(
        "/api/v1/products",
        json=_product_payload(f"{unique}-b", category="Apparel", is_active=False),
    )
    gadgets = auth_client.get(
        "/api/v1/products", params={"search": unique, "category": "Gadgets"}
    ).json()
    assert gadgets["total"] == 1
    inactive = auth_client.get(
        "/api/v1/products", params={"search": unique, "is_active": False}
    ).json()
    assert inactive["total"] == 1
    assert inactive["items"][0]["category"] == "Apparel"


def test_product_update(auth_client: TestClient, unique: str) -> None:
    created = auth_client.post("/api/v1/products", json=_product_payload(unique))
    product_id = created.json()["id"]
    updated = auth_client.put(
        f"/api/v1/products/{product_id}", json={"unit_price": "59.50", "is_active": False}
    )
    assert updated.status_code == 200
    assert Decimal(str(updated.json()["unit_price"])) == Decimal("59.50")
    assert updated.json()["is_active"] is False


def test_customer_sorting(auth_client: TestClient, unique: str) -> None:
    for first in ("Zara", "Mira", "Arun"):
        auth_client.post(
            "/api/v1/customers",
            json=_customer_payload(f"{unique}-{first}", first_name=first),
        )
    asc = auth_client.get(
        "/api/v1/customers",
        params={"search": unique, "sort_by": "first_name", "order": "asc", "page_size": 10},
    ).json()
    assert [item["first_name"] for item in asc["items"]] == ["Arun", "Mira", "Zara"]
    desc = auth_client.get(
        "/api/v1/customers",
        params={"search": unique, "sort_by": "first_name", "order": "desc", "page_size": 10},
    ).json()
    assert [item["first_name"] for item in desc["items"]] == ["Zara", "Mira", "Arun"]
    default = auth_client.get(
        "/api/v1/customers", params={"search": unique, "page_size": 10}
    ).json()
    ids = [item["id"] for item in default["items"]]
    assert ids == sorted(ids)
    invalid = auth_client.get("/api/v1/customers", params={"search": unique, "sort_by": "nope"})
    assert invalid.status_code == 422
