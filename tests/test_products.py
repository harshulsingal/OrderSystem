from fastapi.testclient import TestClient


def test_create_product(client: TestClient):
    response = client.post(
        "/api/products",
        json={
            "name": "iPhone 15",
            "sku": "IPH15-128-BLK",
            "price": "69999.00",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "iPhone 15"
    assert data["sku"] == "IPH15-128-BLK"
    assert float(data["price"]) == 69999.00
    assert "id" in data
    assert "created_at" in data


def test_get_product(client: TestClient):
    create_resp = client.post(
        "/api/products",
        json={
            "name": "MacBook Pro",
            "sku": "MBP-14-M3",
            "price": "169999.00",
        },
    )
    assert create_resp.status_code == 201
    product_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/products/{product_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "MacBook Pro"
    assert get_resp.json()["sku"] == "MBP-14-M3"


def test_get_all_products(client: TestClient):
    client.post(
        "/api/products",
        json={"name": "Item 1", "sku": "SKU-001", "price": "100.00"},
    )
    client.post(
        "/api/products",
        json={"name": "Item 2", "sku": "SKU-002", "price": "200.00"},
    )

    resp = client.get("/api/products")
    assert resp.status_code == 200
    products = resp.json()
    assert len(products) == 2


def test_duplicate_sku_returns_409(client: TestClient):
    first_resp = client.post(
        "/api/products",
        json={"name": "Item A", "sku": "DUP-SKU", "price": "50.00"},
    )
    assert first_resp.status_code == 201

    second_resp = client.post(
        "/api/products",
        json={"name": "Item B", "sku": "DUP-SKU", "price": "60.00"},
    )
    assert second_resp.status_code == 409
    assert "already exists" in second_resp.json()["detail"]


def test_nonexistent_product_returns_404(client: TestClient):
    resp = client.get("/api/products/999999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]
