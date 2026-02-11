"""
Conversation data models
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ModelConfig(BaseModel):
    """Model configuration"""
    provider: str
    api_key: str
    model_name: str
    base_url: Optional[str] = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str
    conversation_id: Optional[str] = None
    file_context: Optional[str] = None
    llm_config: Optional[ModelConfig] = None
    language: Optional[str] = None  # 语言设置（如 'zh-CN', 'en-US', 'auto' 等）


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    message: str
    conversation_id: str


class Message(BaseModel):
    """Individual message model"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str


class ConversationHistory(BaseModel):
    """Conversation history model"""
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class AgentConfig(BaseModel):
    """Agent mode configuration"""
    enable_mcp: bool = True
    enable_skills: bool = True
    mcp_servers: Optional[dict] = None  # {"ServerName": {"url": "...", "transport": "sse"}}
    max_iterations: int = 10


class AgentRequest(BaseModel):
    """Request model for agent endpoint"""
    message: str
    conversation_id: Optional[str] = None
    file_context: Optional[str] = None
    llm_config: Optional[ModelConfig] = None
    language: Optional[str] = None
    agent_config: Optional[AgentConfig] = None
