"""
Main FastAPI application for AI Chat System
"""

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv

load_dotenv()

import json
import os
from fastapi.responses import StreamingResponse  # type: ignore
from fastapi import FastAPI, UploadFile, File, HTTPException  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from services.llm_service import LLMService
from services.file_service import FileService
from services.conversation_service import ConversationService
from services.agent_service import AgentService
from services.code_service import CodeService
from services.mcp_client import MCPClient, BuiltinMCPTools
from services.skill_manager import SkillManager
from models.conversation import (
    ChatRequest,
    ChatResponse,
    ConversationHistory,
    AgentRequest,
    AgentConfig,
    CodeRequest,
)

app = FastAPI(title="AI Chat System", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm_service = LLMService()
file_service = FileService()
conversation_service = ConversationService()

# Initialize agent services
mcp_client = MCPClient()  # Will be configured per request
skill_manager = SkillManager(workspace_root=os.getcwd())
agent_service = AgentService(mcp_client=mcp_client, skill_manager=skill_manager)

# Initialize code service
code_service = CodeService(llm_service=llm_service)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"status": "ok", "message": "AI Chat System API"}


@app.get("/health")
async def health():
    """Health check endpoint for Docker"""
    return {"status": "healthy", "service": "AI Chat System", "version": "2.1.0"}


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
        import traceback

        print(traceback.format_exc())
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
                from services.mcp_client import MCPClient

                request_mcp_client = MCPClient(servers_config=agent_config.mcp_servers)

            # Generate streaming response
            full_response = ""
            tool_calls_log = []

            async for chunk in agent_service.generate_stream(
                message=request.message,
                conversation_history=history,
                file_context=request.file_context,
                model_config=(
                    request.llm_config.model_dump() if request.llm_config else None
                ),
                language=request.language,
                enable_mcp=agent_config.enable_mcp,
                enable_skills=agent_config.enable_skills,
                max_iterations=agent_config.max_iterations,
                mcp_client_override=request_mcp_client,
            ):
                # Send chunk as SSE
                event_data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

                # Collect response for saving
                if chunk.get("type") == "text":
                    full_response += chunk.get("content", "")
                elif chunk.get("type") == "tool_call":
                    tool_calls_log.append(chunk)

            # Save conversation
            if full_response:
                conversation_id = conversation_service.save_message(
                    conversation_id=request.conversation_id,
                    user_message=request.message,
                    assistant_message=full_response,
                    file_context=request.file_context,
                )

                # Send final metadata
                metadata = {
                    "type": "metadata",
                    "conversation_id": conversation_id,
                    "tool_calls_count": len(tool_calls_log),
                }
                yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback

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
    """
    try:
        tools = []

        # Get MCP tools
        mcp_tools = await mcp_client.list_tools()
        tools.extend(mcp_tools)

        # Get built-in MCP tools
        builtin_tools = BuiltinMCPTools.list_tools()
        tools.extend(builtin_tools)

        # Get custom skills
        skill_tools = skill_manager.get_tools()
        tools.extend(skill_tools)

        return {
            "tools": tools,
            "count": len(tools),
            "categories": {
                "mcp": len(mcp_tools),
                "builtin": len(builtin_tools),
                "skills": len(skill_tools),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/configure")
async def configure_agent(config: AgentConfig):
    """
    Configure agent settings
    """
    try:
        # Update MCP client
        if config.mcp_servers:
            mcp_client.servers_config = config.mcp_servers
            mcp_client.clear_cache()
        else:
            mcp_client.servers_config = {}
            mcp_client.clear_cache()

        return {
            "status": "configured",
            "config": config.model_dump(),
        }
    except Exception as e:
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
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
