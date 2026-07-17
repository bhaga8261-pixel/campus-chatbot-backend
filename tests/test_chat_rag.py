import pytest
from unittest.mock import AsyncMock, patch
from bson import ObjectId
from app.main import app
from app.auth.jwt_handler import get_current_user

# Setup dependency override for current user
mock_user_id = ObjectId("64f5c35b8fc6b04a43b2cf77")
mock_user = {
    "_id": mock_user_id,
    "name": "Test Student",
    "email": "test@college.edu",
    "role": "student"
}

@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.clear()

@patch("app.api.chat.perform_vector_search")
@patch("app.api.chat.generate_rag_answer")
@patch("app.api.chat.get_collection")
def test_chatbot_endpoint_success(mock_get_collection, mock_generate_rag, mock_vector_search, client):
    """Test standard chatbot RAG flow."""
    # 1. Mock vector search result (retrieve 1 document chunk)
    mock_vector_search.return_value = [
        {
            "id": "chunk_123",
            "documentId": "doc_456",
            "chunk": "The semester exam commences on July 20, 2026.",
            "page": 1,
            "metadata": {"document_name": "Syllabus Guide"},
            "score": 0.95,
            "document_name": "Syllabus Guide"
        }
    ]
    
    # 2. Mock LLM response
    mock_generate_rag.return_value = (
        "According to the Syllabus Guide (Page 1), the semester exam starts on July 20, 2026.",
        [{"document_name": "Syllabus Guide", "page": 1, "documentId": "doc_456"}]
    )
    
    # 3. Mock MongoDB write for chats history logging
    mock_chats_col = AsyncMock()
    mock_chats_col.insert_one.return_value = AsyncMock(inserted_id=ObjectId())
    
    # We patch get_collection so it returns our mock collection when "chats" is requested
    def mock_get_col_selector(name):
        if name == "chats":
            return mock_chats_col
        return AsyncMock()
        
    mock_get_collection.side_effect = mock_get_col_selector

    payload = {"question": "When is my semester exam?"}
    response = client.post("/chat", json=payload)
    
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["question"] == "When is my semester exam?"
    assert "July 20, 2026" in res_data["answer"]
    assert len(res_data["sources"]) == 1
    assert res_data["sources"][0]["document_name"] == "Syllabus Guide"
    
    # Verify that we searched and logged
    mock_vector_search.assert_called_once_with("When is my semester exam?", limit=5)
    mock_chats_col.insert_one.assert_called_once()
