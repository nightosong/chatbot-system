"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys
import tempfile
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    os.environ['LLM_API_KEY'] = 'test-api-key-for-testing'
    os.environ['LLM_PROVIDER'] = 'gemini'
    os.environ['MODEL_NAME'] = 'gemini-1.5-flash'


@pytest.fixture
def test_client():
    """Create FastAPI test client"""
    from main import app
    return TestClient(app)


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_conversations.db")
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    os.rmdir(temp_dir)


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for API testing"""
    with patch('main.llm_service') as mock:
        mock.generate_response = AsyncMock(return_value="This is a test response")
        yield mock


@pytest.fixture
def mock_conversation_service():
    """Mock conversation service for API testing"""
    with patch('main.conversation_service') as mock:
        mock.save_message = Mock(return_value="test-conversation-id")
        mock.get_conversation_messages = Mock(return_value=[])
        mock.get_all_conversations = Mock(return_value=[
            {
                "conversation_id": "test-id",
                "title": "Test Conversation",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "message_count": 2
            }
        ])
        yield mock


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing"""
    return [
        {"role": "user", "content": "Hello", "timestamp": "2024-01-01T00:00:00"},
        {"role": "assistant", "content": "Hi there!", "timestamp": "2024-01-01T00:00:01"},
        {"role": "user", "content": "How are you?", "timestamp": "2024-01-01T00:00:02"},
        {"role": "assistant", "content": "I'm doing well!", "timestamp": "2024-01-01T00:00:03"}
    ]


@pytest.fixture
def sample_model_config():
    """Sample model configuration for testing"""
    return {
        "provider": "gemini",
        "api_key": "test-api-key",
        "model_name": "gemini-1.5-flash",
        "base_url": None
    }
