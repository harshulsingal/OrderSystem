import concurrent.futures
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.product import Product
from app.services.inventory_service import reserve_inventory
from app.services.order_service import create_order
from app.schemas.order import OrderCreate, OrderItemCreate


def test_concurrent_inventory_reservations(client: TestClient):
    """
    Test two concurrent reservation requests for 4 units when only 5 are available.
    Verifies PostgreSQL row-level locking (SELECT FOR UPDATE) prevents overselling.
    """
    # 1. Setup product with 5 available units
    prod_resp = client.post(
        "/api/products",
        json={"name": "Limited GPU", "sku": "RTX-5090", "price": "199990.00"},
    )
    product_id = prod_resp.json()["id"]
    client.post("/api/inventory", json={"product_id": product_id, "available_quantity": 5})

    # Function executed concurrently in distinct database sessions
    def attempt_reservation(qty: int):
        db: Session = SessionLocal()
        try:
            inv = reserve_inventory(db, product_id=product_id, quantity=qty)
            return {"success": True, "inv": inv}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    # 2. Run two concurrent requests simultaneously with ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(attempt_reservation, 4)
        f2 = executor.submit(attempt_reservation, 4)
        results = [f1.result(), f2.result()]

    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    # Exactly one must succeed and one must fail
    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got {len(failures)}"
    assert "409" in failures[0]["error"] or "Insufficient inventory" in failures[0]["error"]

    # Verify final state in database: available = 1, reserved = 4
    inv_check = client.get(f"/api/inventory/{product_id}").json()
    assert inv_check["available_quantity"] == 1
    assert inv_check["reserved_quantity"] == 4


def test_concurrent_order_placement(client: TestClient):
    """
    Test two concurrent orders for 4 units each when only 5 units are available.
    """
    prod_resp = client.post(
        "/api/products",
        json={"name": "Limited Edition Sneaker", "sku": "SNK-LIMITED", "price": "15000.00"},
    )
    product_id = prod_resp.json()["id"]
    client.post("/api/inventory", json={"product_id": product_id, "available_quantity": 5})

    def place_order(user_id: int):
        db: Session = SessionLocal()
        try:
            order_in = OrderCreate(
                user_id=user_id,
                items=[OrderItemCreate(product_id=product_id, quantity=4)],
            )
            order = create_order(db, order_in)
            return {"success": True, "order": order}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(place_order, 1)
        f2 = executor.submit(place_order, 2)
        results = [f1.result(), f2.result()]

    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    assert len(successes) == 1
    assert len(failures) == 1
    assert successes[0]["order"].status == "INVENTORY_RESERVED"
    assert "Insufficient inventory" in failures[0]["error"] or "409" in failures[0]["error"]

    # Verify final inventory
    inv_check = client.get(f"/api/inventory/{product_id}").json()
    assert inv_check["available_quantity"] == 1
    assert inv_check["reserved_quantity"] == 4

    # Verify orders in DB: exactly 1 order
    orders_resp = client.get("/api/orders").json()
    assert len(orders_resp) == 1


def test_multi_product_order_rollback_on_insufficient_stock(client: TestClient):
    """
    Test multi-product order where Product A has 10 units (order wants 3)
    and Product B has 2 units (order wants 5).
    Verifies that when Product B fails, the reservation for Product A is rolled back.
    """
    p_a = client.post(
        "/api/products",
        json={"name": "Product A", "sku": "PRD-A", "price": "100.00"},
    ).json()["id"]
    p_b = client.post(
        "/api/products",
        json={"name": "Product B", "sku": "PRD-B", "price": "200.00"},
    ).json()["id"]

    client.post("/api/inventory", json={"product_id": p_a, "available_quantity": 10})
    client.post("/api/inventory", json={"product_id": p_b, "available_quantity": 2})

    # Place order requesting 3 of A and 5 of B
    order_resp = client.post(
        "/api/orders",
        json={
            "user_id": 99,
            "items": [
                {"product_id": p_a, "quantity": 3},
                {"product_id": p_b, "quantity": 5},
            ],
        },
    )

    # Must fail with 409
    assert order_resp.status_code == 409
    assert "Insufficient inventory" in order_resp.json()["detail"]

    # Verify Product A inventory is rolled back: available = 10, reserved = 0
    inv_a = client.get(f"/api/inventory/{p_a}").json()
    assert inv_a["available_quantity"] == 10
    assert inv_a["reserved_quantity"] == 0

    # Verify Product B inventory is untouched: available = 2, reserved = 0
    inv_b = client.get(f"/api/inventory/{p_b}").json()
    assert inv_b["available_quantity"] == 2
    assert inv_b["reserved_quantity"] == 0

    # Verify no order was created in DB
    orders_resp = client.get("/api/orders").json()
    assert len(orders_resp) == 0
