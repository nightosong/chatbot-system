"""
Main FastAPI application for AI Chat System
"""

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv

load_dotenv()

import warnings
import json
import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse  # type: ignore
from fastapi import FastAPI, UploadFile, File, HTTPException  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
from starlette.requests import Request  # type: ignore
from starlette.responses import Response  # type: ignore

from services.llm_service import LLMService
from services.file_service import FileService
from services.conversation_service import ConversationService
from services.agent_service import AgentService
from services.code_service import CodeService
from services.mcp_client import MCPClient, BuiltinMCPTools
from services.skill_manager import SkillManager
from services.logging_service import setup_logging, tail_log_file
from models.conversation import (
    ChatRequest,
    ChatResponse,
    ConversationHistory,
    AgentRequest,
    AgentConfig,
    CodeRequest,
)

warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)

LOG_DIR = os.getenv(
    "APP_LOG_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"),
)
LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "INFO")
LOG_FILE = setup_logging(log_dir=LOG_DIR, level=LOG_LEVEL)
logger = logging.getLogger("ai_chat.backend")

# Initialize services
llm_service = LLMService()
file_service = FileService()
conversation_service = ConversationService()
BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))

# Initialize skill manager as singleton (shared across all requests)
skill_manager = SkillManager.get_instance(
    workspace_root=BACKEND_ROOT,
    skills_root=os.path.join(BACKEND_ROOT, "skills"),
)

# Note: AgentService is now created per-request to support different MCP configurations
# MCP client is also created per-request based on agent config

# Initialize code service
code_service = CodeService(llm_service=llm_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle hooks."""
    try:
        result = await skill_manager.load_skills_from_source(skill_manager.skills_root)
        if result.get("loaded_count", 0) > 0:
            logger.info(
                "Loaded local skills on startup: count=%s names=%s",
                result.get("loaded_count"),
                ",".join(result.get("loaded_skills", [])),
            )
    except Exception as e:
        logger.warning("Skip local skill auto-load: %s", str(e))
    yield


app = FastAPI(title="AI Chat System", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SkillLoadRequest(BaseModel):
    """Request model for loading dynamic skills"""

    source: str
    force_update: bool = False


class SkillLoadResponse(BaseModel):
    """Response model for loading dynamic skills"""

    source: str
    resolved_path: str
    loaded_skills: List[str]
    loaded_count: int
    errors: List[str]


class SkillListResponse(BaseModel):
    """Response model for listing registered skills"""

    skills: List[Dict[str, Any]]
    count: int


class LogTailResponse(BaseModel):
    """Response model for backend log tail API"""

    log_file: str
    total: int
    lines: List[str]


@app.get("/")
async def root():
    """Root endpoint"""
    return {"status": "ok", "message": "AI Chat System API"}


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    client_ip = request.client.host if request.client else "-"
    skip_access_log = request.url.path == "/api/logs"
    try:
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if not skip_access_log:
            logger.info(
                "HTTP %s %s status=%s ip=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                client_ip,
                elapsed_ms,
            )
        return response
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000
        if not skip_access_log:
            logger.exception(
                "HTTP %s %s status=500 ip=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                client_ip,
                elapsed_ms,
            )
        raise


@app.get("/health")
async def health():
    """Health check endpoint for Docker"""
    return {"status": "healthy", "service": "AI Chat System", "version": "2.1.0"}


@app.get("/api/logs", response_model=LogTailResponse)
async def get_backend_logs(
    lines: int = 200,
    level: Optional[str] = None,
    contains: Optional[str] = None,
):
    """
    Read backend log tail for UI viewer.
    """
    try:
        return tail_log_file(
            log_file=LOG_FILE,
            lines=lines,
            level=level,
            contains=contains,
        )
    except Exception as e:
        logger.exception("Failed to read logs")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint
    Handles multi-turn conversations with optional file context
    """
    try:
        # Get conversation history if conversation_id is provided
        history = []
        if request.conversation_id:
            history = conversation_service.get_conversation_messages(
                request.conversation_id
            )

        # Generate response using LLM
        # 如果请求中包含模型配置，使用该配置；否则使用默认配置
        response = await llm_service.generate_response(
            message=request.message,
            conversation_history=history,
            file_context=request.file_context,
            model_config=(
                request.llm_config.model_dump() if request.llm_config else None
            ),
            language=request.language,  # 传递语言设置
        )

        # Save conversation
        conversation_id = conversation_service.save_message(
            conversation_id=request.conversation_id,
            user_message=request.message,
            assistant_message=response,
            file_context=request.file_context,
        )

        return ChatResponse(message=response, conversation_id=conversation_id)
    except Exception as e:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload and process file with intelligent handling
    Supports text, image, video, and audio formats

    Returns:
        - content: Processed text (may be summarized for large files)
        - filename: Original filename
        - original_length: Original text length
        - is_summarized: Whether content was summarized
        - processing_strategy: Strategy used (direct/chunked_summary/aggressive_summary)
    """
    try:
        result = await file_service.process_file(file)
        return {
            "filename": result["filename"],
            "content": result["content"],
            "original_length": result["original_length"],
            "processed_length": len(result["content"]),
            "is_summarized": result["is_summarized"],
            "processing_strategy": result["processing_strategy"],
            "compression_ratio": result.get("compression_ratio", "100%"),
        }
    except Exception as e:
        logger.exception(
            "File upload failed: filename=%s", getattr(file, "filename", "")
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/conversations", response_model=List[ConversationHistory])
async def get_conversations():
    """
    Get all conversation histories
    """
    try:
        conversations = conversation_service.get_all_conversations()
        return conversations
    except Exception as e:
        logger.exception("Get conversations failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get specific conversation by ID
    """
    try:
        messages = conversation_service.get_conversation_messages(conversation_id)
        return {"conversation_id": conversation_id, "messages": messages}
    except Exception as e:
        logger.exception("Get conversation failed: conversation_id=%s", conversation_id)
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation
    """
    try:
        conversation_service.delete_conversation(conversation_id)
        return {"status": "deleted", "conversation_id": conversation_id}
    except Exception as e:
        logger.exception(
            "Delete conversation failed: conversation_id=%s", conversation_id
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/chat")
async def agent_chat(request: AgentRequest):
    """
    Agent mode chat endpoint with streaming support
    Supports MCP tools and custom skills

    Returns Server-Sent Events (SSE) stream with:
    - text chunks
    - tool calls
    - tool results
    - thinking process
    """

    async def event_generator():
        """Generate SSE events"""
        try:
            # Get conversation history
            history = []
            if request.conversation_id:
                history = conversation_service.get_conversation_messages(
                    request.conversation_id
                )

            # Configure agent
            agent_config = request.agent_config or AgentConfig()

            # Create a new MCP client for this request with the specific config
            request_mcp_client = None
            if agent_config.enable_mcp and agent_config.mcp_servers:
                request_mcp_client = MCPClient(servers_config=agent_config.mcp_servers)

            # Create a per-request AgentService instance
            # This allows each request to have its own MCP configuration
            request_agent_service = AgentService(
                mcp_client=request_mcp_client,
                skill_manager=skill_manager  # Share the global skill manager singleton
            )

            # Generate streaming response
            full_response = ""
            tool_calls_log = []
            final_messages = []

            async for chunk in request_agent_service.generate_stream(
                message=request.message,
                conversation_history=history,
                file_context=request.file_context,
                model_config=(
                    request.llm_config.model_dump() if request.llm_config else None
                ),
                language=request.language,
                enable_mcp=agent_config.enable_mcp,
                enable_skills=agent_config.enable_skills,
                selected_skill_names=agent_config.selected_skills,
                max_iterations=agent_config.max_iterations,
            ):
                # Capture final messages for saving
                if chunk.get("type") == "done" and "messages" in chunk:
                    final_messages = chunk["messages"]
                    # Don't send this to client, handle it internally
                    continue

                # Send chunk as SSE
                event_data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

                # Collect response for saving
                if chunk.get("type") == "text":
                    full_response += chunk.get("content", "")
                elif chunk.get("type") == "tool_call":
                    tool_calls_log.append(chunk)

            # Save conversation with complete message history
            if final_messages:
                conversation_id = conversation_service.save_messages(
                    messages=final_messages,
                    conversation_id=request.conversation_id,
                )

                # Send final metadata
                metadata = {
                    "type": "metadata",
                    "conversation_id": conversation_id,
                    "tool_calls_count": len(tool_calls_log),
                }
                yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"

            # Send final done event
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback

            logger.exception("Agent stream failed")
            error_data = {
                "type": "error",
                "content": str(e),
                "traceback": traceback.format_exc(),
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/agent/tools")
async def get_agent_tools():
    """
    Get available agent tools (MCP + Skills)
    Note: Returns built-in MCP tools only. Per-request MCP tools are configured dynamically.
    """
    try:
        tools = []

        # Get built-in MCP tools (always available)
        builtin_tools = BuiltinMCPTools.list_tools()
        tools.extend(builtin_tools)

        return {
            "tools": tools,
            "count": len(tools),
            "categories": {
                "builtin": len(builtin_tools),
            },
            "note": "Per-request MCP tools are configured dynamically via agent_config.mcp_servers"
        }
    except Exception as e:
        logger.exception("Get agent tools failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/skills", response_model=SkillListResponse)
async def list_agent_skills():
    """
    List registered skills, including built-in and dynamically loaded skills.
    """
    try:
        skills = skill_manager.list_skills()
        return {"skills": skills, "count": len(skills)}
    except Exception as e:
        logger.exception("List agent skills failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/skills/load", response_model=SkillLoadResponse)
async def load_agent_skill(request: SkillLoadRequest):
    """
    Dynamically load skills from a GitHub repository URL or local path.
    """
    try:
        result = await skill_manager.load_skills_from_source(
            source=request.source,
            force_update=request.force_update,
        )
        return result
    except ValueError as e:
        logger.warning(
            "Load skill validation failed: source=%s, error=%s", request.source, str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Load skill failed: source=%s", request.source)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/configure")
async def configure_agent(config: AgentConfig):
    """
    Configure agent settings

    Note: With per-request AgentService, MCP configuration is now passed
    directly in each chat request via agent_config.mcp_servers.
    This endpoint is kept for backward compatibility but may be deprecated.
    """
    try:
        return {
            "status": "configured",
            "config": config.model_dump(),
            "note": "AgentService now uses per-request configuration. Pass mcp_servers in agent_config for each request."
        }
    except Exception as e:
        logger.exception("Configure agent failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/code/chat")
async def code_chat(request: CodeRequest):
    """
    Code mode chat endpoint with streaming and tool calling
    Provides file operations, bash execution, and code intelligence

    Returns Server-Sent Events (SSE) stream with:
    - text chunks
    - tool calls (read, write, edit, bash, glob, grep)
    - tool results
    - permission requests
    """

    async def event_generator():
        """Generate SSE events"""
        try:
            # Set workspace root (default to current directory or from request)
            workspace_root = request.workspace_root or os.getcwd()

            # Initialize code service for this request
            request_code_service = CodeService(
                workspace_root=workspace_root, llm_service=llm_service
            )

            # Generate streaming response with tool calling
            async for chunk in request_code_service.generate_code_stream(
                message=request.message,
                conversation_history=request.history or [],
                model_config=(
                    request.llm_config.model_dump() if request.llm_config else None
                ),
                language=request.language,
                max_iterations=request.max_iterations,
            ):
                # Forward all events to client
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback

            logger.exception("Code stream failed")
            error_data = {
                "type": "error",
                "content": str(e),
                "traceback": traceback.format_exc(),
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/code/tools")
async def get_code_tools():
    """
    Get available code mode tools
    """
    try:
        # Get tool definitions from code service
        temp_code_service = CodeService()
        tools = temp_code_service._get_code_tools()

        return {
            "tools": tools,
            "count": len(tools),
            "workspace_root": os.getcwd(),
        }
    except Exception as e:
        logger.exception("Get code tools failed")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
