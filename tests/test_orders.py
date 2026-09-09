from fastapi.testclient import TestClient


def test_create_order_single_item(client: TestClient):
    prod_resp = client.post(
        "/api/products",
        json={"name": "iPhone 15", "sku": "IPH15-BLK", "price": "70000.00"},
    )
    product_id = prod_resp.json()["id"]

    # Set up inventory
    client.post(
        "/api/inventory",
        json={"product_id": product_id, "available_quantity": 10},
    )

    order_resp = client.post(
        "/api/orders",
        json={
            "user_id": 1,
            "items": [{"product_id": product_id, "quantity": 2}],
        },
    )
    assert order_resp.status_code == 201
    data = order_resp.json()
    assert data["user_id"] == 1
    assert data["status"] == "INVENTORY_RESERVED"
    assert float(data["total_amount"]) == 140000.00
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product_id
    assert data["items"][0]["quantity"] == 2
    assert float(data["items"][0]["price"]) == 70000.00

    # Verify inventory was reserved
    inv_resp = client.get(f"/api/inventory/{product_id}")
    assert inv_resp.json()["available_quantity"] == 8
    assert inv_resp.json()["reserved_quantity"] == 2


def test_create_order_multiple_items_total_calculation(client: TestClient):
    p1 = client.post(
        "/api/products",
        json={"name": "Keyboard", "sku": "KB-01", "price": "150.00"},
    ).json()["id"]
    p2 = client.post(
        "/api/products",
        json={"name": "Mouse", "sku": "MS-01", "price": "50.00"},
    ).json()["id"]

    client.post("/api/inventory", json={"product_id": p1, "available_quantity": 10})
    client.post("/api/inventory", json={"product_id": p2, "available_quantity": 10})

    order_resp = client.post(
        "/api/orders",
        json={
            "user_id": 42,
            "items": [
                {"product_id": p1, "quantity": 2},  # 2 * 150 = 300
                {"product_id": p2, "quantity": 3},  # 3 * 50 = 150
            ],
        },
    )
    assert order_resp.status_code == 201
    data = order_resp.json()
    assert data["status"] == "INVENTORY_RESERVED"
    assert float(data["total_amount"]) == 450.00
    assert len(data["items"]) == 2


def test_create_order_nonexistent_product_returns_404(client: TestClient):
    order_resp = client.post(
        "/api/orders",
        json={
            "user_id": 1,
            "items": [{"product_id": 999999, "quantity": 1}],
        },
    )
    assert order_resp.status_code == 404
    assert "not found" in order_resp.json()["detail"]


def test_get_order_by_id(client: TestClient):
    p = client.post(
        "/api/products",
        json={"name": "Monitor", "sku": "MON-4K", "price": "400.00"},
    ).json()["id"]
    client.post("/api/inventory", json={"product_id": p, "available_quantity": 5})

    created = client.post(
        "/api/orders",
        json={
            "user_id": 10,
            "items": [{"product_id": p, "quantity": 1}],
        },
    ).json()

    order_id = created["id"]
    get_resp = client.get(f"/api/orders/{order_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == order_id
    assert data["user_id"] == 10
    assert data["status"] == "INVENTORY_RESERVED"
    assert float(data["total_amount"]) == 400.00
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == p


def test_get_orders_filtering_by_user(client: TestClient):
    p = client.post(
        "/api/products",
        json={"name": "Cable", "sku": "CBL-01", "price": "10.00"},
    ).json()["id"]
    client.post("/api/inventory", json={"product_id": p, "available_quantity": 10})

    client.post(
        "/api/orders",
        json={
            "user_id": 100,
            "items": [{"product_id": p, "quantity": 1}],
        },
    )
    client.post(
        "/api/orders",
        json={
            "user_id": 200,
            "items": [{"product_id": p, "quantity": 2}],
        },
    )

    all_orders = client.get("/api/orders").json()
    assert len(all_orders) == 2

    user_100_orders = client.get("/api/orders?user_id=100").json()
    assert len(user_100_orders) == 1
    assert user_100_orders[0]["user_id"] == 100
