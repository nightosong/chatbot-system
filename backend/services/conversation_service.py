"""
Conversation Service - Handles conversation history persistence
Uses SQLite for local storage
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Optional
import uuid
import os


class ConversationService:
    """Service for managing conversation history"""
    
    def __init__(self, db_path: str = "data/conversations.db"):
        """Initialize conversation service with SQLite database"""
        self.db_path = db_path
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT,
                file_context TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_message(
        self,
        user_message: str,
        assistant_message: str,
        conversation_id: Optional[str] = None,
        file_context: Optional[str] = None
    ) -> str:
        """
        Save a message pair (user + assistant) to database
        
        Args:
            user_message: User's message
            assistant_message: AI's response
            conversation_id: Existing conversation ID or None for new conversation
            file_context: Optional file content context
            
        Returns:
            conversation_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create new conversation if needed
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            title = self._generate_title(user_message)
            now = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conversation_id, title, now, now)
            )
        else:
            # Update conversation timestamp
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id)
            )
        
        # Save user message
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp, file_context) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, "user", user_message, timestamp, file_context)
        )
        
        # Save assistant message
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp, file_context) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, "assistant", assistant_message, timestamp, None)
        )
        
        conn.commit()
        conn.close()
        
        return conversation_id
    
    def get_conversation_messages(self, conversation_id: str) -> List[dict]:
        """
        Get all messages for a conversation
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of message dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp",
            (conversation_id,)
        )
        
        messages = [
            {"role": row[0], "content": row[1], "timestamp": row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return messages
    
    def get_all_conversations(self) -> List[dict]:
        """
        Get all conversations with metadata
        
        Returns:
            List of conversation summaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.id,
                c.title,
                c.created_at,
                c.updated_at,
                COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
        """)
        
        conversations = [
            {
                "conversation_id": row[0],
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3],
                "message_count": row[4]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return conversations
    
    def delete_conversation(self, conversation_id: str):
        """Delete a conversation and all its messages"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        
        conn.commit()
        conn.close()
    
    def _generate_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate conversation title from first message"""
        title = first_message.strip()
        if len(title) > max_length:
            title = title[:max_length] + "..."
        return title
