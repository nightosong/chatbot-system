"""
Unit tests for Conversation Service
"""

import pytest  # type: ignore
import os
import tempfile
from services.conversation_service import ConversationService


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
def conversation_service(temp_db):
    """Create ConversationService instance with temp database"""
    return ConversationService(db_path=temp_db)


def test_init_db(conversation_service):
    """Test database initialization"""
    assert os.path.exists(conversation_service.db_path)


def test_save_new_conversation(conversation_service):
    """Test saving a new conversation"""
    user_msg = "Hello, AI!"
    assistant_msg = "Hello! How can I help you?"

    conversation_id = conversation_service.save_message(
        user_message=user_msg, assistant_message=assistant_msg
    )

    assert conversation_id is not None
    assert len(conversation_id) > 0


def test_save_to_existing_conversation(conversation_service):
    """Test adding messages to existing conversation"""
    # First message
    conversation_id = conversation_service.save_message(
        user_message="First message", assistant_message="First response"
    )

    # Second message to same conversation
    same_id = conversation_service.save_message(
        user_message="Second message",
        assistant_message="Second response",
        conversation_id=conversation_id,
    )

    assert same_id == conversation_id

    # Verify both messages are there
    messages = conversation_service.get_conversation_messages(conversation_id)
    assert len(messages) == 4  # 2 user + 2 assistant


def test_get_conversation_messages(conversation_service):
    """Test retrieving conversation messages"""
    conversation_id = conversation_service.save_message(
        user_message="Test question", assistant_message="Test answer"
    )

    messages = conversation_service.get_conversation_messages(conversation_id)

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Test question"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Test answer"


def test_get_all_conversations(conversation_service):
    """Test retrieving all conversations"""
    # Create multiple conversations
    conversation_service.save_message("Message 1", "Response 1")
    conversation_service.save_message("Message 2", "Response 2")
    conversation_service.save_message("Message 3", "Response 3")

    conversations = conversation_service.get_all_conversations()

    assert len(conversations) == 3
    assert all("conversation_id" in conv for conv in conversations)
    assert all("title" in conv for conv in conversations)
    assert all("message_count" in conv for conv in conversations)


def test_delete_conversation(conversation_service):
    """Test deleting a conversation"""
    conversation_id = conversation_service.save_message("Delete me", "OK")

    # Verify it exists
    conversations = conversation_service.get_all_conversations()
    assert len(conversations) == 1

    # Delete it
    conversation_service.delete_conversation(conversation_id)

    # Verify it's gone
    conversations = conversation_service.get_all_conversations()
    assert len(conversations) == 0


def test_save_with_file_context(conversation_service):
    """Test saving message with file context"""
    file_content = "This is file content"
    conversation_id = conversation_service.save_message(
        user_message="What's in the file?",
        assistant_message="The file contains...",
        file_context=file_content,
    )

    messages = conversation_service.get_conversation_messages(conversation_id)
    assert len(messages) == 2


def test_generate_title(conversation_service):
    """Test title generation"""
    # Short message
    short_title = conversation_service._generate_title("Hello")
    assert short_title == "Hello"

    # Long message
    long_message = "A" * 100
    long_title = conversation_service._generate_title(long_message)
    assert len(long_title) <= 53  # 50 + "..."
    assert long_title.endswith("...")


def test_conversation_ordering(conversation_service):
    """Test conversations are ordered by update time"""
    id1 = conversation_service.save_message("First", "Response 1")
    id2 = conversation_service.save_message("Second", "Response 2")

    # Add message to first conversation (should update its timestamp)
    conversation_service.save_message(
        "New message", "New response", conversation_id=id1
    )

    conversations = conversation_service.get_all_conversations()

    # First conversation should now be at the top (most recent)
    assert conversations[0]["conversation_id"] == id1
