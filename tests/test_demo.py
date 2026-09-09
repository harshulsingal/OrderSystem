from decimal import Decimal
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.schemas.demo import DemoProduct


def test_demo_generate_invalid_count_zero(client: TestClient):
    resp = client.post("/api/demo/generate", json={"count": 0})
    assert resp.status_code == 422


def test_demo_generate_invalid_count_too_large(client: TestClient):
    resp = client.post("/api/demo/generate", json={"count": 25})
    assert resp.status_code == 422


@patch("app.services.openai_service.generate_demo_products")
def test_demo_generate_success(mock_openai, client: TestClient):
    mock_openai.return_value = [
        DemoProduct(
            name="Smart Fitness Band",
            sku="FIT-BAND-01",
            price=Decimal("2999.00"),
            initial_inventory=50,
        ),
        DemoProduct(
            name="Mechanical Gaming Keyboard",
            sku="MECH-KB-RGB",
            price=Decimal("4999.00"),
            initial_inventory=20,
        ),
    ]

    resp = client.post("/api/demo/generate", json={"count": 2})
    assert resp.status_code == 201
    data = resp.json()
    assert data["count"] == 2
    assert "2 products generated successfully" in data["message"]
    assert len(data["items"]) == 2

    # Check first item product & inventory
    item0 = data["items"][0]
    assert item0["product"]["name"] == "Smart Fitness Band"
    assert item0["product"]["sku"] == "FIT-BAND-01"
    assert float(item0["product"]["price"]) == 2999.00
    assert item0["inventory"]["available_quantity"] == 50
    assert item0["inventory"]["reserved_quantity"] == 0

    # Verify products exist via standard API
    products_resp = client.get("/api/products")
    assert products_resp.status_code == 200
    assert len(products_resp.json()) == 2

    # Verify inventory exists via standard API
    p_id = item0["product"]["id"]
    inv_resp = client.get(f"/api/inventory/{p_id}")
    assert inv_resp.status_code == 200
    assert inv_resp.json()["available_quantity"] == 50


@patch("app.services.openai_service.generate_demo_products")
def test_demo_generate_handles_duplicate_sku(mock_openai, client: TestClient):
    # Pre-create product with SKU 'EXISTING-SKU'
    client.post(
        "/api/products",
        json={"name": "Pre-existing", "sku": "EXISTING-SKU", "price": "100.00"},
    )

    mock_openai.return_value = [
        DemoProduct(
            name="New Item with Same SKU",
            sku="EXISTING-SKU",
            price=Decimal("500.00"),
            initial_inventory=10,
        )
    ]

    resp = client.post("/api/demo/generate", json={"count": 1})
    assert resp.status_code == 201
    data = resp.json()
    new_sku = data["items"][0]["product"]["sku"]
    assert new_sku.startswith("EXISTING-SKU-")
    assert new_sku != "EXISTING-SKU"
