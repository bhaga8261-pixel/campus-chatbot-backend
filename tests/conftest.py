import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def client():
    """Fixture to provide a TestClient instance with app lifecycle events."""
    with TestClient(app) as test_client:
        yield test_client
