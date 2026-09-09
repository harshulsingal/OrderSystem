from fastapi.testclient import TestClient


def test_empty_product_name_rejected(client: TestClient):
    resp = client.post(
        "/api/products",
        json={"name": "   ", "sku": "VALID-SKU", "price": "100.00"},
    )
    assert resp.status_code == 422


def test_invalid_price_zero_rejected(client: TestClient):
    resp = client.post(
        "/api/products",
        json={"name": "Freebie", "sku": "FREE-SKU", "price": "0.00"},
    )
    assert resp.status_code == 422


def test_invalid_price_negative_rejected(client: TestClient):
    resp = client.post(
        "/api/products",
        json={"name": "Negative", "sku": "NEG-SKU", "price": "-10.00"},
    )
    assert resp.status_code == 422


def test_order_item_zero_quantity_rejected(client: TestClient):
    p = client.post(
        "/api/products",
        json={"name": "Sample", "sku": "SMP-01", "price": "50.00"},
    ).json()["id"]

    resp = client.post(
        "/api/orders",
        json={
            "user_id": 1,
            "items": [{"product_id": p, "quantity": 0}],
        },
    )
    assert resp.status_code == 422


def test_order_item_negative_quantity_rejected(client: TestClient):
    p = client.post(
        "/api/products",
        json={"name": "Sample2", "sku": "SMP-02", "price": "50.00"},
    ).json()["id"]

    resp = client.post(
        "/api/orders",
        json={
            "user_id": 1,
            "items": [{"product_id": p, "quantity": -5}],
        },
    )
    assert resp.status_code == 422


def test_inventory_negative_quantity_rejected(client: TestClient):
    p = client.post(
        "/api/products",
        json={"name": "Sample3", "sku": "SMP-03", "price": "50.00"},
    ).json()["id"]

    resp = client.post(
        "/api/inventory",
        json={"product_id": p, "available_quantity": -10},
    )
    assert resp.status_code == 422
