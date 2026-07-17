import pytest
from unittest.mock import AsyncMock, patch
from bson import ObjectId
from app.auth.jwt_handler import hash_password

@patch("app.api.auth.get_collection")
def test_register_new_student(mock_get_collection, client):
    """Test successful user registration as student."""
    mock_users_col = AsyncMock()
    # Mock that user does not exist yet
    mock_users_col.find_one.return_value = None
    mock_users_col.count_documents.return_value = 1 # Not first user
    mock_users_col.insert_one.return_value = AsyncMock(inserted_id=ObjectId())
    
    mock_get_collection.return_value = mock_users_col

    payload = {
        "name": "Aman Verma",
        "email": "aman@college.edu",
        "password": "securepassword123",
        "role": "student"
    }
    
    response = client.post("/auth/register", json=payload)
    
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["name"] == payload["name"]
    assert res_data["email"] == payload["email"]
    assert res_data["role"] == "student"
    assert "password" not in res_data

@patch("app.api.auth.get_collection")
def test_register_duplicate_email(mock_get_collection, client):
    """Test registration fails if email is already taken."""
    mock_users_col = AsyncMock()
    # Mock that user already exists
    mock_users_col.find_one.return_value = {"_id": ObjectId(), "email": "taken@college.edu"}
    
    mock_get_collection.return_value = mock_users_col

    payload = {
        "name": "Duplicate User",
        "email": "taken@college.edu",
        "password": "securepassword123",
        "role": "student"
    }
    
    response = client.post("/auth/register", json=payload)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

@patch("app.api.auth.get_collection")
def test_login_successful(mock_get_collection, client):
    """Test successful login returns a JWT token."""
    mock_users_col = AsyncMock()
    hashed = hash_password("mypassword")
    
    mock_users_col.find_one.return_value = {
        "_id": ObjectId(),
        "name": "Test User",
        "email": "test@college.edu",
        "password": hashed,
        "role": "student"
    }
    
    mock_get_collection.return_value = mock_users_col

    payload = {
        "email": "test@college.edu",
        "password": "mypassword"
    }
    
    response = client.post("/auth/login", json=payload)
    
    assert response.status_code == 200
    res_data = response.json()
    assert "access_token" in res_data
    assert res_data["token_type"] == "bearer"
    assert res_data["role"] == "student"
    assert res_data["name"] == "Test User"
