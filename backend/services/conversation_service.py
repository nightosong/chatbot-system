"""
Conversation Service - Handles conversation history persistence
Uses SQLite for local storage
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
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
                metadata TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)

        # Agent runs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY,
                conversation_id TEXT,
                request_payload TEXT,
                status TEXT,
                summary TEXT,
                error_message TEXT,
                started_at TEXT,
                finished_at TEXT,
                updated_at TEXT,
                interrupt_requested INTEGER DEFAULT 0,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
            """
        )

        # Agent run event log
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                seq INTEGER,
                event_type TEXT,
                payload TEXT,
                timestamp TEXT,
                FOREIGN KEY (run_id) REFERENCES agent_runs(run_id)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_run_events_run_seq ON agent_run_events(run_id, seq)"
        )
        
        conn.commit()
        conn.close()
    

    def create_conversation(self, title: Optional[str] = None) -> dict:
        """Create an empty conversation/project and return its metadata"""
        conversation_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conversation_title = (title or "新对话").strip() or "新对话"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conversation_id, conversation_title, now, now)
        )
        conn.commit()
        conn.close()

        return {
            "conversation_id": conversation_id,
            "project_id": conversation_id,
            "title": conversation_title,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
        }

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

    def save_messages(
        self,
        messages: List[dict],
        conversation_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> str:
        """
        Save multiple messages to database (supports tool calls and complete message history)

        Args:
            messages: List of message dictionaries with role, content, and optional metadata
            conversation_id: Existing conversation ID or None for new conversation
            title: Optional conversation title (for new conversations)

        Returns:
            conversation_id
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create new conversation if needed
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            # Generate title from first user message if not provided
            if not title:
                first_user_msg = next((m for m in messages if m.get("role") == "user"), None)
                if first_user_msg:
                    title = self._generate_title(first_user_msg.get("content", "New conversation"))
                else:
                    title = "New conversation"

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

        # Save all messages
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            timestamp = msg.get("timestamp") or datetime.now().isoformat()
            file_context = msg.get("file_context")

            metadata: Dict[str, Any] = {}
            explicit_metadata = msg.get("metadata")
            if isinstance(explicit_metadata, dict):
                metadata.update(explicit_metadata)

            for key, value in msg.items():
                if key in {"role", "content", "timestamp", "file_context", "metadata"}:
                    continue
                metadata[key] = value

            metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

            cursor.execute(
                "INSERT INTO messages (conversation_id, role, content, timestamp, file_context, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (conversation_id, role, content, timestamp, file_context, metadata_json)
            )

        conn.commit()
        conn.close()

        return conversation_id
    
    def save_agent_run_confirmation(
        self,
        conversation_id: str,
        run_started_at: str,
        step_timestamp: str,
        selected_action: str,
    ) -> bool:
        """Persist selected confirmation action into assistant message metadata."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, metadata FROM messages WHERE conversation_id = ? AND role = ? ORDER BY timestamp DESC",
            (conversation_id, "assistant"),
        )

        target_message_id = None
        updated_metadata = None

        for message_id, metadata_raw in cursor.fetchall():
            if not metadata_raw:
                continue
            try:
                metadata = json.loads(metadata_raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(metadata, dict):
                continue

            agent_run = metadata.get("agent_run")
            if not isinstance(agent_run, dict):
                continue
            if agent_run.get("started_at") != run_started_at:
                continue

            confirmations = agent_run.get("confirmations")
            if not isinstance(confirmations, dict):
                confirmations = {}
            confirmations[step_timestamp] = selected_action
            agent_run["confirmations"] = confirmations
            metadata["agent_run"] = agent_run
            target_message_id = message_id
            updated_metadata = json.dumps(metadata, ensure_ascii=False)
            break

        if target_message_id is None or updated_metadata is None:
            conn.close()
            raise ValueError("Agent run not found for confirmation update")

        cursor.execute(
            "UPDATE messages SET metadata = ? WHERE id = ?",
            (updated_metadata, target_message_id),
        )
        cursor.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), conversation_id),
        )
        conn.commit()
        conn.close()
        return True

    def get_conversation_messages(self, conversation_id: str) -> List[dict]:
        """
        Get all messages for a conversation (including tool calls metadata)

        Args:
            conversation_id: Conversation ID

        Returns:
            List of message dictionaries with full context
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT role, content, timestamp, metadata FROM messages WHERE conversation_id = ? ORDER BY timestamp",
            (conversation_id,)
        )

        messages = []
        for row in cursor.fetchall():
            msg = {
                "role": row[0],
                "content": row[1],
                "timestamp": row[2]
            }

            # Deserialize metadata if present
            if row[3]:
                try:
                    metadata = json.loads(row[3])
                    if isinstance(metadata, dict):
                        msg["metadata"] = metadata
                        if "tool_calls" in metadata:
                            msg["tool_calls"] = metadata["tool_calls"]
                        if "tool_call_id" in metadata:
                            msg["tool_call_id"] = metadata["tool_call_id"]
                except json.JSONDecodeError:
                    pass  # Ignore invalid metadata

            messages.append(msg)

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
                "project_id": row[0],
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

    def create_agent_run(
        self, conversation_id: Optional[str], request_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new persisted agent run."""
        run_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        payload_json = (
            json.dumps(request_payload, ensure_ascii=False) if request_payload else None
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO agent_runs (
                run_id, conversation_id, request_payload, status,
                started_at, updated_at, interrupt_requested
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, conversation_id, payload_json, "running", now, now, 0),
        )
        conn.commit()
        conn.close()
        return {
            "run_id": run_id,
            "conversation_id": conversation_id,
            "status": "running",
            "started_at": now,
            "updated_at": now,
            "interrupt_requested": False,
        }

    def append_agent_run_event(self, run_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """Persist one agent run event and return with sequence."""
        now = datetime.now().isoformat()
        event_type = str(event.get("type", "unknown"))
        payload_json = json.dumps(event, ensure_ascii=False)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM agent_run_events WHERE run_id = ?",
            (run_id,),
        )
        next_seq = int(cursor.fetchone()[0])
        cursor.execute(
            """
            INSERT INTO agent_run_events (run_id, seq, event_type, payload, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, next_seq, event_type, payload_json, now),
        )
        cursor.execute(
            "UPDATE agent_runs SET updated_at = ? WHERE run_id = ?",
            (now, run_id),
        )
        conn.commit()
        conn.close()

        enriched = dict(event)
        enriched["run_id"] = run_id
        enriched["seq"] = next_seq
        enriched.setdefault("timestamp", now)
        return enriched

    def get_agent_run_events(
        self, run_id: str, after_seq: int = 0, limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Get persisted events for one run after a sequence."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT seq, payload, timestamp
            FROM agent_run_events
            WHERE run_id = ? AND seq > ?
            ORDER BY seq ASC
            LIMIT ?
            """,
            (run_id, after_seq, limit),
        )

        events: List[Dict[str, Any]] = []
        for seq, payload_raw, timestamp in cursor.fetchall():
            try:
                payload = json.loads(payload_raw) if payload_raw else {}
            except json.JSONDecodeError:
                payload = {}
            if not isinstance(payload, dict):
                payload = {"type": "unknown", "content": str(payload)}
            payload["run_id"] = run_id
            payload["seq"] = int(seq)
            payload.setdefault("timestamp", timestamp)
            events.append(payload)

        conn.close()
        return events

    def get_agent_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get a single agent run by run_id."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT run_id, conversation_id, status, summary, error_message,
                   started_at, finished_at, updated_at, interrupt_requested
            FROM agent_runs
            WHERE run_id = ?
            """,
            (run_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "run_id": row[0],
            "conversation_id": row[1],
            "status": row[2],
            "summary": row[3],
            "error_message": row[4],
            "started_at": row[5],
            "finished_at": row[6],
            "updated_at": row[7],
            "interrupt_requested": bool(row[8]),
        }

    def update_agent_run(
        self,
        run_id: str,
        *,
        status: Optional[str] = None,
        summary: Optional[str] = None,
        error_message: Optional[str] = None,
        conversation_id: Optional[str] = None,
        finished_at: Optional[str] = None,
    ) -> None:
        """Update mutable fields for one agent run."""
        update_fields: List[str] = []
        values: List[Any] = []
        if status is not None:
            update_fields.append("status = ?")
            values.append(status)
        if summary is not None:
            update_fields.append("summary = ?")
            values.append(summary)
        if error_message is not None:
            update_fields.append("error_message = ?")
            values.append(error_message)
        if conversation_id is not None:
            update_fields.append("conversation_id = ?")
            values.append(conversation_id)
        if finished_at is not None:
            update_fields.append("finished_at = ?")
            values.append(finished_at)

        now = datetime.now().isoformat()
        update_fields.append("updated_at = ?")
        values.append(now)
        values.append(run_id)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE agent_runs SET {', '.join(update_fields)} WHERE run_id = ?",
            tuple(values),
        )
        conn.commit()
        conn.close()

    def request_agent_run_interrupt(self, run_id: str) -> bool:
        """Mark one run as interruption requested."""
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE agent_runs SET interrupt_requested = 1, updated_at = ? WHERE run_id = ?",
            (now, run_id),
        )
        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return changed

    def is_agent_run_interrupt_requested(self, run_id: str) -> bool:
        """Check whether run has interruption request."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT interrupt_requested FROM agent_runs WHERE run_id = ?",
            (run_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return bool(row[0]) if row else False
