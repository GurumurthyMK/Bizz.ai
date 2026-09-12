"""Data import/health tests: validation, safety, integrity, authorization.

Uploads run against the isolated SQLite database through the real API;
multipart bodies are built in-memory, never from disk.
"""

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.customer import Customer
from app.models.product import Product
from app.models.transaction import Transaction


def _csv_bytes(rows: list[dict[str, str]], columns: list[str]) -> bytes:
    import csv

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _upload(
    client: TestClient,
    path: str,
    entity: str,
    filename: str,
    payload: bytes,
    content_type: str = "text/csv",
):
    return client.post(
        f"/api/v1/data/{path}?entity={entity}",
        files={"file": (filename, payload, content_type)},
    )


@pytest.fixture()
def seeded_refs(auth_client: TestClient, unique: str) -> dict[str, str]:
    """One customer + product + campaign the transaction/interaction files can reference."""
    email = f"ref-{unique}@example.com"
    assert (
        auth_client.post(
            "/api/v1/customers",
            json={"first_name": "Ref", "last_name": "Erence", "email": email},
        ).status_code
        == 201
    )
    assert (
        auth_client.post(
            "/api/v1/products",
            json={
                "sku": f"SKU-REF-{unique}",
                "name": "Ref Widget",
                "category": "Gadgets",
                "unit_price": "49.99",
            },
        ).status_code
        == 201
    )
    assert (
        auth_client.post(
            "/api/v1/campaigns",
            json={
                "name": f"Campaign Ref-{unique}",
                "channel": "email",
                "campaign_type": "seasonal",
            },
        ).status_code
        == 201
    )
    return {"email": email, "sku": f"SKU-REF-{unique}", "campaign": f"Campaign Ref-{unique}"}


def test_data_routes_require_authentication(client: TestClient) -> None:
    payload = b"first_name,last_name,email\nA,B,c@example.com\n"
    assert (
        client.post(
            "/api/v1/data/preview?entity=customers",
            files={"file": ("a.csv", payload, "text/csv")},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/data/import?entity=customers",
            files={"file": ("a.csv", payload, "text/csv")},
        ).status_code
        == 401
    )
    assert client.get("/api/v1/data/health").status_code == 401
    assert client.get("/api/v1/data/imports").status_code == 401


def test_preview_and_import_valid_customers(auth_client: TestClient, unique: str) -> None:
    columns = ["first_name", "last_name", "email", "city"]
    rows = [
        {
            "first_name": "Ana",
            "last_name": "Pop",
            "email": f"ana-{unique}@example.com",
            "city": "Cluj",
        },
        {
            "first_name": "Bob",
            "last_name": "Rex",
            "email": f"bob-{unique}@example.com",
            "city": "",
        },
    ]
    preview = auth_client.post(
        "/api/v1/data/preview?entity=customers",
        files={"file": ("customers.csv", _csv_bytes(rows, columns), "text/csv")},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["total_rows"] == 2
    assert body["valid_rows"] == 2
    assert body["invalid_rows"] == 0
    assert body["errors"] == []
    assert len(body["sample"]) == 2

    result = auth_client.post(
        "/api/v1/data/import?entity=customers",
        files={"file": ("customers.csv", _csv_bytes(rows, columns), "text/csv")},
    )
    assert result.status_code == 200
    assert result.json()["rows_inserted"] == 2

    health = auth_client.get("/api/v1/data/health").json()
    assert health["counts"]["customers"] >= 2
    assert health["last_import"]["entity"] == "customers"
    assert health["last_import"]["status"] == "completed"


def test_import_missing_columns_rejected(auth_client: TestClient, unique: str) -> None:
    payload = _csv_bytes(
        [{"first_name": "Ana", "email": f"ana-{unique}@example.com"}],
        ["first_name", "email"],
    )
    preview = auth_client.post(
        "/api/v1/data/preview?entity=customers",
        files={"file": ("c.csv", payload, "text/csv")},
    ).json()
    assert preview["valid_rows"] == 0
    assert any(error["column"] == "last_name" for error in preview["errors"])

    before = auth_client.get("/api/v1/data/health").json()["counts"]["customers"]
    response = auth_client.post(
        "/api/v1/data/import?entity=customers",
        files={"file": ("c.csv", payload, "text/csv")},
    )
    assert response.status_code == 422
    after = auth_client.get("/api/v1/data/health").json()["counts"]["customers"]
    assert after == before


def test_import_malformed_rows_reported_with_lines(
    auth_client: TestClient, unique: str, seeded_refs: dict[str, str]
) -> None:
    columns = ["customer_email", "product_sku", "quantity", "unit_price", "transaction_date"]
    rows = [
        {
            "customer_email": seeded_refs["email"],
            "product_sku": seeded_refs["sku"],
            "quantity": "2",
            "unit_price": "10.00",
            "transaction_date": "2026-08-01T10:00:00Z",
        },
        {
            "customer_email": seeded_refs["email"],
            "product_sku": seeded_refs["sku"],
            "quantity": "two",
            "unit_price": "10.00",
            "transaction_date": "2026-08-02T10:00:00Z",
        },
        {
            "customer_email": seeded_refs["email"],
            "product_sku": seeded_refs["sku"],
            "quantity": "1",
            "unit_price": "10.00",
            "transaction_date": "not-a-date",
        },
        {
            "customer_email": "ghost@example.com",
            "product_sku": seeded_refs["sku"],
            "quantity": "1",
            "unit_price": "10.00",
            "transaction_date": "2026-08-03T10:00:00Z",
        },
    ]
    preview = auth_client.post(
        "/api/v1/data/preview?entity=transactions",
        files={"file": ("t.csv", _csv_bytes(rows, columns), "text/csv")},
    ).json()
    assert preview["valid_rows"] == 1
    assert preview["invalid_rows"] == 3
    by_line = {error["line"]: error for error in preview["errors"]}
    assert by_line[3]["column"] == "quantity"
    assert by_line[4]["column"] == "transaction_date"
    assert by_line[5]["column"] == "customer_email"

    before = auth_client.get("/api/v1/data/health").json()["counts"]["transactions"]
    response = auth_client.post(
        "/api/v1/data/import?entity=transactions",
        files={"file": ("t.csv", _csv_bytes(rows, columns), "text/csv")},
    )
    assert response.status_code == 422
    after = auth_client.get("/api/v1/data/health").json()["counts"]["transactions"]
    assert after == before  # all-or-nothing: the valid row is not persisted either


def test_import_rejects_bad_file_types(auth_client: TestClient) -> None:
    payload = b"first_name,last_name,email\nA,B,c@example.com\n"
    assert (
        auth_client.post(
            "/api/v1/data/import?entity=customers",
            files={"file": ("evil.exe", payload, "application/x-msdownload")},
        ).status_code
        == 400
    )
    assert (
        auth_client.post(
            "/api/v1/data/import?entity=customers",
            files={"file": ("notes.txt", payload, "text/plain")},
        ).status_code
        == 400
    )
    assert (
        auth_client.post(
            "/api/v1/data/import?entity=customers",
            files={"file": ("empty.csv", b"", "text/csv")},
        ).status_code
        == 400
    )
    assert (
        auth_client.post(
            "/api/v1/data/import?entity=customers",
            files={"file": ("header-only.csv", b"first_name,last_name,email\n", "text/csv")},
        ).status_code
        == 400
    )


def test_import_rejects_oversize_file(auth_client: TestClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import app.services.data_import as data_import

    monkeypatch.setattr(data_import, "MAX_CSV_BYTES", 10)
    payload = b"first_name,last_name,email\nA,B,c@example.com\n"
    assert (
        auth_client.post(
            "/api/v1/data/import?entity=customers",
            files={"file": ("big.csv", payload, "text/csv")},
        ).status_code
        == 400
    )


def test_import_rejects_duplicate_and_conflicting_skus(
    auth_client: TestClient, unique: str
) -> None:
    columns = ["sku", "name", "category", "unit_price"]
    first = auth_client.post(
        "/api/v1/data/import?entity=products",
        files={
            "file": (
                "p.csv",
                _csv_bytes(
                    [
                        {
                            "sku": f"SKU-DUP-{unique}",
                            "name": "One",
                            "category": "G",
                            "unit_price": "5",
                        }
                    ],
                    columns,
                ),
                "text/csv",
            )
        },
    )
    assert first.status_code == 200

    # Same SKU twice inside one file (fresh SKU, so the file-level check fires).
    dupe_file = auth_client.post(
        "/api/v1/data/import?entity=products",
        files={
            "file": (
                "p.csv",
                _csv_bytes(
                    [
                        {
                            "sku": f"SKU-FILE-{unique}",
                            "name": "Two",
                            "category": "G",
                            "unit_price": "6",
                        },
                        {
                            "sku": f"SKU-FILE-{unique}",
                            "name": "Three",
                            "category": "G",
                            "unit_price": "7",
                        },
                    ],
                    columns,
                ),
                "text/csv",
            )
        },
    )
    assert dupe_file.status_code == 422
    assert any("uplicate" in error["message"] for error in dupe_file.json()["detail"])

    # SKU already in the database.
    conflict = auth_client.post(
        "/api/v1/data/import?entity=products",
        files={
            "file": (
                "p.csv",
                _csv_bytes(
                    [
                        {
                            "sku": f"SKU-DUP-{unique}",
                            "name": "Four",
                            "category": "G",
                            "unit_price": "8",
                        }
                    ],
                    columns,
                ),
                "text/csv",
            )
        },
    )
    assert conflict.status_code == 422


def test_import_campaigns_and_interactions(
    auth_client: TestClient, unique: str, seeded_refs: dict[str, str]
) -> None:
    campaigns = auth_client.post(
        "/api/v1/data/import?entity=campaigns",
        files={
            "file": (
                "c.csv",
                _csv_bytes(
                    [
                        {
                            "name": f"Summer-{unique}",
                            "channel": "email",
                            "campaign_type": "seasonal",
                            "status": "active",
                            "budget": "1000",
                        },
                        {
                            "name": f"Bad-{unique}",
                            "channel": "pigeon",
                            "campaign_type": "seasonal",
                            "status": "active",
                        },
                    ],
                    ["name", "channel", "campaign_type", "status", "budget"],
                ),
                "text/csv",
            )
        },
    )
    assert campaigns.status_code == 422
    assert any(error["column"] == "channel" for error in campaigns.json()["detail"])

    interactions = auth_client.post(
        "/api/v1/data/import?entity=interactions",
        files={
            "file": (
                "i.csv",
                _csv_bytes(
                    [
                        {
                            "customer_email": seeded_refs["email"],
                            "campaign_name": seeded_refs["campaign"],
                            "interaction_type": "open",
                            "channel": "email",
                            "occurred_at": "2026-08-10T09:00:00Z",
                        },
                        {
                            "customer_email": seeded_refs["email"],
                            "interaction_type": "visit",
                            "channel": "web",
                            "occurred_at": "2026-08-11T09:00:00Z",
                        },
                    ],
                    [
                        "customer_email",
                        "campaign_name",
                        "interaction_type",
                        "channel",
                        "occurred_at",
                    ],
                ),
                "text/csv",
            )
        },
    )
    assert interactions.status_code == 200
    assert interactions.json()["rows_inserted"] == 2


def test_large_import_performs(auth_client: TestClient, unique: str) -> None:
    columns = ["first_name", "last_name", "email"]
    rows = [
        {"first_name": "Bulk", "last_name": f"User{i}", "email": f"bulk-{unique}-{i}@example.com"}
        for i in range(2000)
    ]
    response = auth_client.post(
        "/api/v1/data/import?entity=customers",
        files={"file": ("bulk.csv", _csv_bytes(rows, columns), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["rows_inserted"] == 2000


def test_import_jobs_and_health_integrity(
    auth_client: TestClient, unique: str, seeded_refs: dict[str, str]
) -> None:
    auth_client.post(
        "/api/v1/data/import?entity=customers",
        files={
            "file": (
                "j.csv",
                _csv_bytes(
                    [{"first_name": "Jo", "last_name": "B", "email": f"jo-{unique}@example.com"}],
                    ["first_name", "last_name", "email"],
                ),
                "text/csv",
            ),
        },
    )
    customers = auth_client.get("/api/v1/customers", params={"page_size": 1}).json()["items"]
    products = auth_client.get("/api/v1/products", params={"page_size": 1}).json()["items"]
    assert customers and products
    auth_client.post(
        "/api/v1/transactions",
        json={
            "customer_id": customers[0]["id"],
            "product_id": products[0]["id"],
            "quantity": 1,
            "unit_price": "10.00",
            "transaction_date": "2026-08-12T10:00:00Z",
        },
    )
    jobs = auth_client.get("/api/v1/data/imports").json()
    assert jobs["total"] >= 1
    assert jobs["items"][0]["status"] == "completed"

    health = auth_client.get("/api/v1/data/health").json()
    assert set(health["counts"]) == {
        "customers",
        "products",
        "transactions",
        "campaigns",
        "interactions",
    }
    assert health["integrity"]["orphan_transactions"] == 0
    assert health["integrity"]["orphan_interactions"] == 0
    assert health["freshness"]["transaction_date_max"] is not None
    assert health["last_import"]["entity"] == "customers"


def test_import_totals_match_service_math(
    auth_client: TestClient, unique: str, seeded_refs: dict[str, str]
) -> None:
    auth_client.post(
        "/api/v1/data/import?entity=transactions",
        files={
            "file": (
                "m.csv",
                _csv_bytes(
                    [
                        {
                            "customer_email": seeded_refs["email"],
                            "product_sku": seeded_refs["sku"],
                            "quantity": "3",
                            "unit_price": "49.99",
                            "discount": "10.00",
                            "transaction_date": "2026-08-12T10:00:00Z",
                        }
                    ],
                    [
                        "customer_email",
                        "product_sku",
                        "quantity",
                        "unit_price",
                        "discount",
                        "transaction_date",
                    ],
                ),
                "text/csv",
            ),
        },
    )
    from tests.conftest import TestingSession

    with TestingSession() as db:
        total = db.scalar(
            select(Transaction.total_amount).where(
                Transaction.customer_id
                == db.scalar(select(Customer.id).where(Customer.email == seeded_refs["email"])),
                Transaction.product_id
                == db.scalar(select(Product.id).where(Product.sku == seeded_refs["sku"])),
            )
        )
    assert total is not None and float(total) == round(3 * 49.99 - 10.00, 2)
