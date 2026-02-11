"""
Unit tests for API endpoints
测试所有 FastAPI 端点的功能
"""
import pytest
from unittest.mock import patch, AsyncMock


def test_root_endpoint(test_client):
    """Test root health check endpoint"""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_chat_new_conversation(test_client, mock_llm_service, mock_conversation_service):
    """Test chat endpoint with new conversation"""
    request_data = {
        "message": "Hello, AI!",
        "conversation_id": None,
        "file_context": None,
        "llm_config": None
    }
    
    response = test_client.post("/api/chat", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "conversation_id" in data
    assert data["conversation_id"] == "test-conversation-id"


def test_chat_existing_conversation(test_client, mock_llm_service, mock_conversation_service):
    """Test chat endpoint with existing conversation"""
    mock_conversation_service.get_conversation_messages.return_value = [
        {"role": "user", "content": "Previous message", "timestamp": "2024-01-01T00:00:00"},
        {"role": "assistant", "content": "Previous response", "timestamp": "2024-01-01T00:00:01"}
    ]
    
    request_data = {
        "message": "Follow-up question",
        "conversation_id": "existing-id",
        "file_context": None
    }
    
    response = test_client.post("/api/chat", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_chat_with_file_context(test_client, mock_llm_service, mock_conversation_service):
    """Test chat endpoint with file context"""
    request_data = {
        "message": "What's in this file?",
        "conversation_id": None,
        "file_context": "File content here..."
    }
    
    response = test_client.post("/api/chat", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_chat_with_model_config(test_client, mock_llm_service, mock_conversation_service):
    """Test chat endpoint with user model configuration"""
    request_data = {
        "message": "Hello with custom model!",
        "conversation_id": None,
        "file_context": None,
        "llm_config": {
            "provider": "gemini",
            "api_key": "test-key",
            "model_name": "gemini-1.5-flash",
            "base_url": None
        }
    }
    
    response = test_client.post("/api/chat", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_get_conversations(test_client, mock_conversation_service):
    """Test get all conversations endpoint"""
    response = test_client.get("/api/conversations")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["conversation_id"] == "test-id"


def test_get_specific_conversation(test_client, mock_conversation_service):
    """Test get specific conversation endpoint"""
    mock_conversation_service.get_conversation_messages.return_value = [
        {"role": "user", "content": "Test", "timestamp": "2024-01-01T00:00:00"}
    ]
    
    response = test_client.get("/api/conversations/test-id")
    
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == "test-id"
    assert "messages" in data


def test_delete_conversation(test_client, mock_conversation_service):
    """Test delete conversation endpoint"""
    response = test_client.delete("/api/conversations/test-id")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"
    assert data["conversation_id"] == "test-id"


@pytest.mark.asyncio
async def test_upload_file_txt(test_client):
    """Test file upload endpoint with text file"""
    file_content = b"Hello, this is a test file."
    
    with patch('main.file_service') as mock_file_service:
        mock_file_service.process_file = AsyncMock(return_value={
            "filename": "test.txt",
            "content": "Hello, this is a test file.",
            "original_length": 28,
            "is_summarized": False,
            "processing_strategy": "direct"
        })
        
        response = test_client.post(
            "/api/upload",
            files={"file": ("test.txt", file_content, "text/plain")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.txt"
        assert "content" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
