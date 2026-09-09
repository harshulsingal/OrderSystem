from fastapi.testclient import TestClient


def _create_order(client: TestClient, sku: str, quantity: int = 1) -> dict:
    product = client.post(
        "/api/products",
        json={"name": "Test Product", "sku": sku, "price": "100.00"},
    ).json()
    client.post(
        "/api/inventory",
        json={"product_id": product["id"], "available_quantity": 10},
    )
    order = client.post(
        "/api/orders",
        json={
            "user_id": 1,
            "items": [{"product_id": product["id"], "quantity": quantity}],
        },
    ).json()
    return order


def test_get_payments_empty(client: TestClient):
    resp = client.get("/api/payments")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_payment_nonexistent_returns_404(client: TestClient):
    resp = client.get("/api/payments/999999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_create_payment_success_marks_order_paid(client: TestClient):
    order = _create_order(client, "PAY-OK-1")

    resp = client.post(
        "/api/payments",
        json={"order_id": order["id"], "idempotency_key": "key-success-1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["order_id"] == order["id"]
    assert data["payment_reference"] is not None

    order_resp = client.get(f"/api/orders/{order['id']}")
    assert order_resp.json()["status"] == "PAID"


def test_create_payment_is_idempotent_on_retry(client: TestClient):
    order = _create_order(client, "PAY-IDEMP-1")

    first = client.post(
        "/api/payments",
        json={"order_id": order["id"], "idempotency_key": "retry-key-1"},
    ).json()
    second = client.post(
        "/api/payments",
        json={"order_id": order["id"], "idempotency_key": "retry-key-1"},
    ).json()

    assert first["id"] == second["id"]
    assert first["payment_reference"] == second["payment_reference"]

    # Only one payment record was ever created for this idempotency key
    payments = client.get("/api/payments").json()
    matching = [p for p in payments if p["idempotency_key"] == "retry-key-1"]
    assert len(matching) == 1


def test_create_payment_failure_releases_inventory_and_marks_order_failed(
    client: TestClient,
):
    order = _create_order(client, "PAY-FAIL-1", quantity=3)

    resp = client.post(
        "/api/payments",
        json={"order_id": order["id"], "idempotency_key": "FAIL-simulated-decline"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "FAILED"

    order_resp = client.get(f"/api/orders/{order['id']}").json()
    assert order_resp["status"] == "PAYMENT_FAILED"

    product_id = order["items"][0]["product_id"]
    inv = client.get(f"/api/inventory/{product_id}").json()
    # Reserved stock from order creation was released back to available
    assert inv["available_quantity"] == 10
    assert inv["reserved_quantity"] == 0


def test_create_payment_for_nonexistent_order_returns_404(client: TestClient):
    resp = client.post(
        "/api/payments", json={"order_id": 999999, "idempotency_key": "nope"}
    )
    assert resp.status_code == 404


def test_create_payment_for_already_paid_order_returns_409(client: TestClient):
    order = _create_order(client, "PAY-DUP-ORDER-1")
    client.post(
        "/api/payments",
        json={"order_id": order["id"], "idempotency_key": "first-charge"},
    )

    resp = client.post(
        "/api/payments",
        json={"order_id": order["id"], "idempotency_key": "second-charge"},
    )
    assert resp.status_code == 409
