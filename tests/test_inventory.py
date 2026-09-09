from fastapi.testclient import TestClient


def test_create_inventory(client: TestClient):
    prod_resp = client.post(
        "/api/products",
        json={"name": "AirPods Pro", "sku": "APP-GEN2", "price": "24900.00"},
    )
    product_id = prod_resp.json()["id"]

    inv_resp = client.post(
        "/api/inventory",
        json={"product_id": product_id, "available_quantity": 50},
    )
    assert inv_resp.status_code == 201
    data = inv_resp.json()
    assert data["product_id"] == product_id
    assert data["available_quantity"] == 50
    assert data["reserved_quantity"] == 0
    assert "id" in data


def test_duplicate_inventory_returns_409(client: TestClient):
    prod_resp = client.post(
        "/api/products",
        json={"name": "iPad Air", "sku": "IPAD-AIR-M2", "price": "59900.00"},
    )
    product_id = prod_resp.json()["id"]

    first_inv = client.post(
        "/api/inventory",
        json={"product_id": product_id, "available_quantity": 30},
    )
    assert first_inv.status_code == 201

    second_inv = client.post(
        "/api/inventory",
        json={"product_id": product_id, "available_quantity": 10},
    )
    assert second_inv.status_code == 409
    assert "already exists" in second_inv.json()["detail"]


def test_inventory_for_nonexistent_product_returns_404(client: TestClient):
    resp = client.post(
        "/api/inventory",
        json={"product_id": 999999, "available_quantity": 10},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_get_inventory(client: TestClient):
    prod_resp = client.post(
        "/api/products",
        json={"name": "Magic Mouse", "sku": "MM-WHT", "price": "7500.00"},
    )
    product_id = prod_resp.json()["id"]

    client.post(
        "/api/inventory",
        json={"product_id": product_id, "available_quantity": 100},
    )

    get_resp = client.get(f"/api/inventory/{product_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["product_id"] == product_id
    assert data["available_quantity"] == 100


def test_get_all_inventories(client: TestClient):
    p1 = client.post(
        "/api/products",
        json={"name": "P1", "sku": "SKU-P1", "price": "10.00"},
    ).json()["id"]
    p2 = client.post(
        "/api/products",
        json={"name": "P2", "sku": "SKU-P2", "price": "20.00"},
    ).json()["id"]

    client.post(
        "/api/inventory", json={"product_id": p1, "available_quantity": 5}
    )
    client.post(
        "/api/inventory", json={"product_id": p2, "available_quantity": 15}
    )

    resp = client.get("/api/inventory")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_reserve_inventory_success(client: TestClient):
    prod_id = client.post(
        "/api/products",
        json={"name": "Kindle", "sku": "KNDL-01", "price": "9999.00"},
    ).json()["id"]
    client.post("/api/inventory", json={"product_id": prod_id, "available_quantity": 10})

    resp = client.post(f"/api/inventory/{prod_id}/reserve", json={"quantity": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["available_quantity"] == 7
    assert data["reserved_quantity"] == 3


def test_reserve_inventory_insufficient_returns_409(client: TestClient):
    prod_id = client.post(
        "/api/products",
        json={"name": "PS5", "sku": "PS5-DIGI", "price": "44990.00"},
    ).json()["id"]
    client.post("/api/inventory", json={"product_id": prod_id, "available_quantity": 2})

    resp = client.post(f"/api/inventory/{prod_id}/reserve", json={"quantity": 5})
    assert resp.status_code == 409
    assert "Insufficient inventory" in resp.json()["detail"]


def test_release_inventory_success(client: TestClient):
    prod_id = client.post(
        "/api/products",
        json={"name": "Xbox", "sku": "XBX-SERX", "price": "49990.00"},
    ).json()["id"]
    client.post("/api/inventory", json={"product_id": prod_id, "available_quantity": 10})

    # Reserve 4
    client.post(f"/api/inventory/{prod_id}/reserve", json={"quantity": 4})

    # Release 2
    resp = client.post(f"/api/inventory/{prod_id}/release", json={"quantity": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["available_quantity"] == 8
    assert data["reserved_quantity"] == 2


def test_release_inventory_more_than_reserved_returns_409(client: TestClient):
    prod_id = client.post(
        "/api/products",
        json={"name": "Switch", "sku": "NSW-OLED", "price": "29990.00"},
    ).json()["id"]
    client.post("/api/inventory", json={"product_id": prod_id, "available_quantity": 10})

    # Reserve 2
    client.post(f"/api/inventory/{prod_id}/reserve", json={"quantity": 2})

    # Attempt to release 5
    resp = client.post(f"/api/inventory/{prod_id}/release", json={"quantity": 5})
    assert resp.status_code == 409
    assert "Cannot release" in resp.json()["detail"]
