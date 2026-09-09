import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="function")
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session):
    # Clear test tables before each test for clean isolation
    db_session.query(Payment).delete()
    db_session.query(OrderItem).delete()
    db_session.query(Order).delete()
    db_session.query(Inventory).delete()
    db_session.query(Product).delete()
    db_session.commit()

    with TestClient(app) as test_client:
        yield test_client

    # Clean up after test as well
    db_session.query(Payment).delete()
    db_session.query(OrderItem).delete()
    db_session.query(Order).delete()
    db_session.query(Inventory).delete()
    db_session.query(Product).delete()
    db_session.commit()
