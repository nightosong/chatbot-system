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
from datetime import datetime
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
from services.agent_service_v2 import AgentServiceV2
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
    CreateConversationRequest,
    CreateConversationResponse,
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


class AgentRunConfirmationRequest(BaseModel):
    """Request model for persisting confirmation action state"""

    run_started_at: str
    step_timestamp: str
    selected_action: str


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
        # Get conversation/project history if provided
        history = []
        active_conversation_id = request.conversation_id or request.project_id
        if active_conversation_id:
            history = conversation_service.get_conversation_messages(
                active_conversation_id
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
            conversation_id=(request.conversation_id or request.project_id),
            user_message=request.message,
            assistant_message=response,
            file_context=request.file_context,
        )

        return ChatResponse(
            message=response,
            conversation_id=conversation_id,
            project_id=conversation_id,
        )
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


@app.post("/api/conversations", response_model=CreateConversationResponse)
async def create_conversation(request: CreateConversationRequest):
    """Create an empty conversation and return its id immediately"""
    try:
        return conversation_service.create_conversation(title=request.title)
    except Exception as e:
        logger.exception("Create conversation failed")
        raise HTTPException(status_code=500, detail=str(e))


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
        return {
            "conversation_id": conversation_id,
            "project_id": conversation_id,
            "messages": messages,
        }
    except Exception as e:
        logger.exception("Get conversation failed: conversation_id=%s", conversation_id)
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/conversations/{conversation_id}/agent-runs/confirm")
async def save_agent_run_confirmation(
    conversation_id: str, request: AgentRunConfirmationRequest
):
    """Persist selected confirmation action for an agent run."""
    try:
        conversation_service.save_agent_run_confirmation(
            conversation_id=conversation_id,
            run_started_at=request.run_started_at,
            step_timestamp=request.step_timestamp,
            selected_action=request.selected_action,
        )
        return {
            "status": "ok",
            "conversation_id": conversation_id,
            "run_started_at": request.run_started_at,
            "step_timestamp": request.step_timestamp,
            "selected_action": request.selected_action,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(
            "Failed to persist agent confirmation: conversation_id=%s run_started_at=%s",
            conversation_id,
            request.run_started_at,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation
    """
    try:
        conversation_service.delete_conversation(conversation_id)
        return {
            "status": "deleted",
            "conversation_id": conversation_id,
            "project_id": conversation_id,
        }
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
        started_at = datetime.now().isoformat()
        agent_run_events = []
        tool_calls_log = []
        final_messages = []
        history = []
        active_conversation_id = request.conversation_id or request.project_id

        def _sanitize_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
            sanitized = dict(chunk)
            sanitized.pop("messages", None)
            sanitized.setdefault("timestamp", datetime.now().isoformat())
            return sanitized

        def _build_persisted_turn_messages(status: str, summary: str) -> List[dict]:
            finished_at = datetime.now().isoformat()
            history_offset = 1 + len(history)
            current_turn_messages = (
                [dict(msg) for msg in final_messages[history_offset:]]
                if final_messages
                else []
            )

            if (
                not current_turn_messages
                or current_turn_messages[0].get("role") != "user"
            ):
                current_turn_messages.insert(
                    0,
                    {
                        "role": "user",
                        "content": request.message,
                        "timestamp": started_at,
                        "file_context": request.file_context,
                    },
                )
            elif not current_turn_messages[0].get("timestamp"):
                current_turn_messages[0]["timestamp"] = started_at
                if request.file_context and not current_turn_messages[0].get(
                    "file_context"
                ):
                    current_turn_messages[0]["file_context"] = request.file_context

            persisted_summary = (summary or "").strip()
            run_payload = {
                "started_at": started_at,
                "finished_at": finished_at,
                "status": status,
                "summary": persisted_summary,
                "tool_calls_count": len(tool_calls_log),
                "events": agent_run_events,
                "anchor_timestamp": current_turn_messages[0].get(
                    "timestamp", started_at
                ),
            }

            assistant_indices = [
                idx
                for idx, msg in enumerate(current_turn_messages)
                if msg.get("role") == "assistant"
            ]
            if assistant_indices:
                target_index = assistant_indices[-1]
                target_message = current_turn_messages[target_index]
                target_message.setdefault("metadata", {})
                target_message["metadata"]["agent_run"] = run_payload
                if not target_message.get("timestamp"):
                    target_message["timestamp"] = finished_at
            else:
                current_turn_messages.append(
                    {
                        "role": "assistant",
                        "content": persisted_summary or "Agent 执行完成",
                        "timestamp": finished_at,
                        "metadata": {"agent_run": run_payload},
                    }
                )

            for msg in current_turn_messages:
                if not msg.get("timestamp"):
                    msg["timestamp"] = finished_at

            return current_turn_messages

        try:
            # Get conversation history
            if active_conversation_id:
                history = conversation_service.get_conversation_messages(
                    active_conversation_id
                )

            # Configure agent
            agent_config = request.agent_config or AgentConfig()

            # Create a new MCP client for this request with the specific config
            request_mcp_client = None
            if agent_config.enable_mcp and agent_config.mcp_servers:
                request_mcp_client = MCPClient(servers_config=agent_config.mcp_servers)

            # Create a per-request AgentService instance
            request_agent_service = AgentService(
                mcp_client=request_mcp_client,
                skill_manager=skill_manager,
            )

            full_response = ""

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
                if chunk.get("type") == "done" and "messages" in chunk:
                    final_messages = chunk["messages"]
                    continue

                agent_run_events.append(_sanitize_chunk(chunk))

                event_data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

                if chunk.get("type") == "text":
                    full_response += chunk.get("content", "")
                elif chunk.get("type") == "tool_call":
                    tool_calls_log.append(chunk)

            persisted_messages = _build_persisted_turn_messages(
                status="completed",
                summary=full_response,
            )
            conversation_id = conversation_service.save_messages(
                messages=persisted_messages,
                conversation_id=active_conversation_id,
            )

            metadata = {
                "type": "metadata",
                "conversation_id": conversation_id,
                "project_id": conversation_id,
                "tool_calls_count": len(tool_calls_log),
            }
            yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback

            logger.exception("Agent stream failed")
            error_data = {
                "type": "error",
                "content": str(e),
                "traceback": traceback.format_exc(),
            }
            agent_run_events.append(_sanitize_chunk(error_data))

            persisted_messages = [
                {
                    "role": "user",
                    "content": request.message,
                    "timestamp": started_at,
                    "file_context": request.file_context,
                },
                {
                    "role": "assistant",
                    "content": f"❌ Agent 执行失败：{str(e)}",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "agent_run": {
                            "started_at": started_at,
                            "finished_at": datetime.now().isoformat(),
                            "status": "error",
                            "summary": f"❌ Agent 执行失败：{str(e)}",
                            "tool_calls_count": len(tool_calls_log),
                            "events": agent_run_events,
                            "anchor_timestamp": started_at,
                        }
                    },
                },
            ]
            conversation_id = conversation_service.save_messages(
                messages=persisted_messages,
                conversation_id=active_conversation_id,
            )
            error_data["conversation_id"] = conversation_id
            error_data["project_id"] = conversation_id
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


@app.post("/api/agent/chat/v2")
async def agent_chat_v2(request: AgentRequest):
    """
    Agent mode chat endpoint V2 with proper Skills architecture
    
    Key differences from V1:
    - Skills are NOT exposed as tools
    - SKILL.md content is loaded on-demand
    - Agent follows skill instructions to call MCP tools
    - Better workflow understanding and execution
    
    Returns Server-Sent Events (SSE) stream with:
    - text chunks
    - tool calls
    - tool results
    - skill activations
    """

    async def event_generator():
        """Generate SSE events"""
        started_at = datetime.now().isoformat()
        agent_run_events = []
        tool_calls_log = []
        final_messages = []
        history = []
        active_conversation_id = request.conversation_id or request.project_id

        def _sanitize_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
            sanitized = dict(chunk)
            sanitized.pop("messages", None)
            sanitized.setdefault("timestamp", datetime.now().isoformat())
            return sanitized

        def _build_persisted_turn_messages(status: str, summary: str) -> List[dict]:
            finished_at = datetime.now().isoformat()
            history_offset = 1 + len(history)
            current_turn_messages = (
                [dict(msg) for msg in final_messages[history_offset:]]
                if final_messages
                else []
            )

            if (
                not current_turn_messages
                or current_turn_messages[0].get("role") != "user"
            ):
                current_turn_messages.insert(
                    0,
                    {
                        "role": "user",
                        "content": request.message,
                        "timestamp": started_at,
                        "file_context": request.file_context,
                    },
                )
            elif not current_turn_messages[0].get("timestamp"):
                current_turn_messages[0]["timestamp"] = started_at
                if request.file_context and not current_turn_messages[0].get(
                    "file_context"
                ):
                    current_turn_messages[0]["file_context"] = request.file_context

            persisted_summary = (summary or "").strip()
            run_payload = {
                "started_at": started_at,
                "finished_at": finished_at,
                "status": status,
                "summary": persisted_summary,
                "tool_calls_count": len(tool_calls_log),
                "events": agent_run_events,
                "anchor_timestamp": current_turn_messages[0].get(
                    "timestamp", started_at
                ),
                "version": "v2",  # Mark as V2 execution
            }

            assistant_indices = [
                idx
                for idx, msg in enumerate(current_turn_messages)
                if msg.get("role") == "assistant"
            ]
            if assistant_indices:
                target_index = assistant_indices[-1]
                target_message = current_turn_messages[target_index]
                target_message.setdefault("metadata", {})
                target_message["metadata"]["agent_run"] = run_payload
                if not target_message.get("timestamp"):
                    target_message["timestamp"] = finished_at
            else:
                current_turn_messages.append(
                    {
                        "role": "assistant",
                        "content": persisted_summary or "Agent 执行完成 (V2)",
                        "timestamp": finished_at,
                        "metadata": {"agent_run": run_payload},
                    }
                )

            for msg in current_turn_messages:
                if not msg.get("timestamp"):
                    msg["timestamp"] = finished_at

            return current_turn_messages

        try:
            # Get conversation history
            if active_conversation_id:
                history = conversation_service.get_messages(active_conversation_id)
            
            # Configure agent
            agent_config = request.agent_config or AgentConfig()
            
            # Create per-request MCP client
            request_mcp_client = None
            if agent_config.enable_mcp and agent_config.mcp_servers:
                request_mcp_client = MCPClient(servers_config=agent_config.mcp_servers)
            
            # Create V2 AgentService instance
            request_agent_service = AgentServiceV2(
                mcp_client=request_mcp_client,
                skill_manager=skill_manager,
            )
            
            # Stream agent response
            last_text_content = []
            async for chunk in request_agent_service.generate_stream(
                message=request.message,
                conversation_history=history,
                file_context=request.file_context,
                model_config=request.model_config,
                language=request.language,
                enable_mcp=agent_config.enable_mcp,
                enable_skills=agent_config.enable_skills,
                selected_skill_names=agent_config.selected_skills,
                max_iterations=agent_config.max_iterations,
            ):
                chunk_type = chunk.get("type")
                
                # Log events
                agent_run_events.append(_sanitize_chunk(chunk))
                
                # Track tool calls
                if chunk_type == "tool_call":
                    tool_calls_log.append(
                        {
                            "tool": chunk.get("tool"),
                            "args": chunk.get("args"),
                            "timestamp": chunk.get("timestamp"),
                        }
                    )
                
                # Collect text content for summary
                if chunk_type == "text":
                    last_text_content.append(chunk.get("content", ""))
                
                # Track final messages
                if chunk_type == "done":
                    final_messages = chunk.get("messages", [])
                
                # Stream to client
                if chunk_type != "done":
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            
            # Build summary
            summary = "".join(last_text_content).strip()
            if not summary:
                summary = "Agent V2 执行完成"
            
            # Save conversation
            persisted_messages = _build_persisted_turn_messages("completed", summary)
            conversation_id = conversation_service.save_messages(
                messages=persisted_messages,
                conversation_id=active_conversation_id,
            )
            
            # Send final event
            done_data = {
                "type": "done",
                "conversation_id": conversation_id,
                "project_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
                "version": "v2",
            }
            yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.exception("Agent V2 stream failed")
            error_data = {
                "type": "error",
                "content": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            agent_run_events.append(_sanitize_chunk(error_data))
            
            # Save error state
            persisted_messages = [
                {
                    "role": "user",
                    "content": request.message,
                    "timestamp": started_at,
                    "file_context": request.file_context,
                },
                {
                    "role": "assistant",
                    "content": f"❌ Agent V2 执行失败：{str(e)}",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "agent_run": {
                            "started_at": started_at,
                            "finished_at": datetime.now().isoformat(),
                            "status": "error",
                            "summary": f"❌ Agent V2 执行失败：{str(e)}",
                            "tool_calls_count": len(tool_calls_log),
                            "events": agent_run_events,
                            "anchor_timestamp": started_at,
                            "version": "v2",
                        }
                    },
                },
            ]
            conversation_id = conversation_service.save_messages(
                messages=persisted_messages,
                conversation_id=active_conversation_id,
            )
            error_data["conversation_id"] = conversation_id
            error_data["project_id"] = conversation_id
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
            "note": "Per-request MCP tools are configured dynamically via agent_config.mcp_servers",
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
            "note": "AgentService now uses per-request configuration. Pass mcp_servers in agent_config for each request.",
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
