"""
Agent Service V2 - Correct Agent + Skills Architecture

This implementation follows Anthropic's Skills standard:
1. Progressive Disclosure: metadata → instruction → resources
2. Skills as Knowledge Containers (not tools)
3. Clear separation: MCP (capabilities) vs Skills (workflows)
4. Agent orchestrates Skills + MCP to complete tasks

Key differences from V1:
- Skills are NOT exposed as tools
- SKILL.md content is loaded on-demand when skill is activated
- Agent follows skill instructions to call MCP tools
- Sandbox is only used for skill scripts (optional)
"""

import json
import os
import threading
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import OpenAI
from services.skill_manager import SkillManager


class AgentServiceV2:
    """Agent service with proper Skills architecture.
    
    Architecture:
    1. System prompt contains skill metadata (name + description)
    2. When a skill is needed, its SKILL.md content is loaded into context
    3. Agent follows skill instructions to orchestrate MCP tool calls
    4. Skills provide workflows; MCP provides capabilities
    """

    # Class-level cache for system prompt
    _default_system_prompt_cache: Optional[str] = None
    _prompt_cache_lock = threading.Lock()

    def __init__(self, mcp_client=None, skill_manager: SkillManager | None = None):
        """
        Initialize Agent Service V2
        
        Args:
            mcp_client: MCP client for tool calling
            skill_manager: Skill manager for loading skill metadata and content
        """
        self.mcp_client = mcp_client
        self.skill_manager = skill_manager
        self._current_model_config: Optional[Dict[str, Any]] = None
        self._current_mcp_config: Optional[Dict[str, Any]] = None
        self._default_system_prompt = self._load_default_system_prompt()
        
        # Track activated skills in current conversation
        self._activated_skills: set[str] = set()

    def _load_default_system_prompt(self) -> str:
        """Load default system prompt with caching."""
        if self._default_system_prompt_cache is not None:
            return self._default_system_prompt_cache

        with self._prompt_cache_lock:
            if self._default_system_prompt_cache is not None:
                return self._default_system_prompt_cache

            prompt_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "prompts",
                "agent_with_skills.md",
            )
            fallback = self._build_default_prompt()

            try:
                with open(prompt_path, "r", encoding="utf-8") as file:
                    content = file.read().strip()
                result = content or fallback
            except Exception:
                result = fallback

            self._default_system_prompt_cache = result
            return result

    def _build_default_prompt(self) -> str:
        """Build default system prompt explaining agent+skills architecture."""
        return """You are an AI assistant with access to Skills and MCP Tools.

# Architecture Overview

**Skills** provide specialized workflows and domain knowledge for complex tasks.
**MCP Tools** provide atomic capabilities (API calls, file operations, etc.).

Your job is to:
1. Identify when a user request matches a Skill
2. Load and follow the Skill's instructions
3. Use MCP Tools as directed by the Skill
4. Complete the task according to the Skill's workflow

# How to Use Skills

When you encounter a task that matches a Skill's description:

1. **Activate the Skill** by saying: "I will use the [skill-name] skill for this task."
2. **Load the Skill instructions** using available read tools to access the SKILL.md file
3. **Follow the workflow** defined in the SKILL.md step by step
4. **Call MCP Tools** as instructed by the workflow
5. **Maintain state** by persisting intermediate results as specified

# Important Rules

- Skills are NOT tools you call directly - they are instructions you follow
- Always read the SKILL.md content before starting the skill's workflow
- Follow the skill's workflow precisely - don't skip steps
- Use MCP tools only as directed by active skills or user requests
- Keep track of workflow state through conversation history and artifacts

# Available Tools

You have access to tools for:
- Reading files (to load SKILL.md and resources)
- Listing directories (to discover skill resources)
- Calling MCP tools (for actual operations)
"""

    def _build_skill_metadata_section(
        self, 
        skills: List[Dict[str, Any]]
    ) -> str:
        """Build skill metadata section for system prompt (Level 1: Progressive Disclosure)."""
        if not skills:
            return ""
        
        sections = ["# Available Skills"]
        sections.append("These skills provide specialized workflows:\n")
        
        for skill in skills:
            name = skill.get("name", "")
            description = skill.get("description", "")
            metadata = skill.get("metadata", {})
            skill_path = metadata.get("path", "")
            
            if not name:
                continue
            
            sections.append(f"## {name}")
            sections.append(f"**Description**: {description}")
            if skill_path:
                sections.append(f"**Location**: {skill_path}/SKILL.md")
            sections.append("")  # blank line
        
        sections.append("\n**To use a skill**: Read its SKILL.md file and follow the workflow instructions.")
        return "\n".join(sections)

    def _build_mcp_tools_section(
        self,
        tools: List[Dict[str, Any]]
    ) -> str:
        """Build MCP tools section for system prompt."""
        if not tools:
            return ""
        
        sections = ["# Available MCP Tools"]
        sections.append("These are atomic operations you can call:\n")
        
        for tool in tools:
            function_info = tool.get("function", {})
            name = function_info.get("name", "")
            description = function_info.get("description", "")
            
            if not name:
                continue
            
            sections.append(f"- **{name}**: {description}")
        
        return "\n".join(sections)

    async def generate_stream(
        self,
        message: str,
        conversation_history: Optional[List[dict]] = None,
        file_context: Optional[str] = None,
        model_config: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
        enable_mcp: bool = True,
        enable_skills: bool = True,
        selected_skill_names: Optional[List[str]] = None,
        max_iterations: int = 15,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming agent response with proper skill architecture.
        
        Yields:
            - {"type": "text", "content": "..."}
            - {"type": "tool_call", "tool": "...", "args": {...}}
            - {"type": "tool_result", "tool": "...", "result": "..."}
            - {"type": "skill_activated", "skill": "...", "content": "..."}
            - {"type": "error", "content": "..."}
            - {"type": "done", "messages": [...]}
        """
        if conversation_history is None:
            conversation_history = []

        try:
            # Validate model config
            if not model_config:
                raise ValueError("Model configuration is required for agent mode")

            provider = model_config.get("provider", "").lower()
            api_key = model_config.get("api_key")
            model_name = model_config.get("model_name")
            base_url = model_config.get("base_url")

            if not api_key or not model_name:
                raise ValueError("API key and model name are required")

            # Store configs for tool execution
            self._current_model_config = model_config
            self._current_mcp_config = (
                self.mcp_client.servers_config if self.mcp_client else None
            )

            # Get MCP tools (NOT skills as tools)
            mcp_tools = []
            if enable_mcp and self.mcp_client:
                mcp_tools = await self.mcp_client.list_tools()

            # Add file system tools for skill access
            filesystem_tools = self._get_filesystem_tools()
            all_tools = mcp_tools + filesystem_tools

            # Get skill metadata (for system prompt only)
            skill_metadata: List[Dict[str, Any]] = []
            if enable_skills and self.skill_manager:
                selected_skill_name_set = set(selected_skill_names or [])
                all_skills = self.skill_manager.list_skills()
                
                if selected_skill_name_set:
                    skill_metadata = [
                        skill for skill in all_skills
                        if skill.get("name") in selected_skill_name_set
                    ]
                else:
                    skill_metadata = all_skills

            # Build messages with proper architecture
            messages = self._build_messages(
                message,
                conversation_history,
                file_context,
                language,
                all_tools,
                skill_metadata,
            )

            final_messages = []

            # Route to provider
            if provider == "gemini":
                async for chunk in self._generate_gemini_stream(
                    api_key, model_name, messages, all_tools, max_iterations
                ):
                    if chunk.get("type") == "done" and "messages" in chunk:
                        final_messages = chunk["messages"]
                    yield chunk
            elif provider == "skywork_router":
                async for chunk in self._generate_skywork_router_stream(
                    api_key, model_name, messages, all_tools, max_iterations
                ):
                    if chunk.get("type") == "done" and "messages" in chunk:
                        final_messages = chunk["messages"]
                    yield chunk
            else:
                async for chunk in self._generate_openai_stream(
                    api_key, model_name, base_url, messages, all_tools, max_iterations
                ):
                    if chunk.get("type") == "done" and "messages" in chunk:
                        final_messages = chunk["messages"]
                    yield chunk

            yield {"type": "done", "messages": final_messages}

        except Exception as e:
            yield {"type": "error", "content": str(e)}

    def _get_filesystem_tools(self) -> List[Dict[str, Any]]:
        """Get file system tools for accessing skill resources."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file (use to load SKILL.md and skill resources)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Absolute or relative path to file"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List files in a directory (use to discover skill resources)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory path"
                            }
                        },
                        "required": ["path"]
                    }
                }
            }
        ]

    def _build_messages(
        self,
        message: str,
        conversation_history: List[dict],
        file_context: Optional[str],
        language: Optional[str],
        available_tools: List[Dict[str, Any]],
        skill_metadata: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build messages with proper skill architecture."""
        messages = []

        # System prompt with skill metadata and MCP tools
        system_content = self._default_system_prompt

        # Add language constraint
        if language and language != "auto":
            language_prompts = {
                "zh-CN": "\n\n请使用简体中文回答所有问题。",
                "en-US": "\n\nPlease answer all questions in English.",
            }
            system_content += language_prompts.get(language, "")

        # Add file context
        if file_context:
            system_content += (
                f"\n\n[File Content]\n{file_context}\n[End of File Content]"
            )

        # Add skill metadata (Level 1: Progressive Disclosure)
        if skill_metadata:
            skill_section = self._build_skill_metadata_section(skill_metadata)
            system_content += "\n\n" + skill_section

        # Add MCP tools section
        if available_tools:
            tools_section = self._build_mcp_tools_section(available_tools)
            system_content += "\n\n" + tools_section

        messages.append({"role": "system", "content": system_content})

        # Add history (last 20 messages)
        if conversation_history:
            for msg in conversation_history[-20:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                if role == "system":
                    continue

                history_msg = {"role": role, "content": content}

                if role == "assistant" and "tool_calls" in msg:
                    history_msg["tool_calls"] = msg["tool_calls"]

                if role == "tool" and "tool_call_id" in msg:
                    history_msg["tool_call_id"] = msg["tool_call_id"]

                if content or "tool_calls" in history_msg:
                    messages.append(history_msg)

        # Add current message
        messages.append({"role": "user", "content": message})

        return messages

    async def _generate_openai_stream(
        self,
        api_key: str,
        model_name: str,
        base_url: Optional[str],
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_iterations: int,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming response with OpenAI-compatible API."""
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        current_messages = messages.copy()
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            api_params = {
                "model": model_name,
                "messages": current_messages,
                "temperature": 0.7,
                "stream": True,
            }

            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = "auto"

            stream = client.chat.completions.create(**api_params)  # type: ignore

            full_content = ""
            tool_calls = []
            current_tool_call = None

            for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                if delta.content:
                    full_content += delta.content
                    yield {"type": "text", "content": delta.content}

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index is not None:
                            if (
                                current_tool_call is None
                                or tc.index != current_tool_call.get("index")
                            ):
                                if current_tool_call:
                                    tool_calls.append(current_tool_call)
                                current_tool_call = {
                                    "index": tc.index,
                                    "id": tc.id or "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }

                            if tc.function:
                                if tc.function.name:
                                    current_tool_call["function"]["name"] = tc.function.name
                                if tc.function.arguments:
                                    current_tool_call["function"]["arguments"] += tc.function.arguments

            if current_tool_call:
                tool_calls.append(current_tool_call)

            if not tool_calls:
                break

            assistant_message = {
                "role": "assistant",
                "content": full_content or None,
                "tool_calls": tool_calls,
            }
            current_messages.append(assistant_message)

            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args_str = tool_call["function"]["arguments"]

                try:
                    tool_args = json.loads(tool_args_str)
                except json.JSONDecodeError:
                    tool_args = {}

                yield {
                    "type": "tool_call",
                    "tool": tool_name,
                    "args": tool_args,
                }

                try:
                    result = await self._execute_tool(tool_name, tool_args)
                    result_str = self._serialize_tool_result(result)
                except Exception as e:
                    result_str = f"Error executing tool: {str(e)}"

                yield {
                    "type": "tool_result",
                    "tool": tool_name,
                    "result": result_str,
                }

                current_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result_str,
                    }
                )

        if iteration >= max_iterations:
            yield {
                "type": "text",
                "content": "\n\n[Reached maximum tool calling iterations]",
            }

        conversation_messages = [msg for msg in current_messages if msg.get("role") != "system"]
        yield {"type": "done", "messages": conversation_messages}

    async def _generate_skywork_router_stream(
        self,
        api_key: str,
        model_name: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_iterations: int,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming response using Skywork Router."""
        import requests
        import asyncio

        url = "https://gpt-us.singularity-ai.com/gpt-proxy/router/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "app_key": api_key,
        }

        current_messages = messages.copy()
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            data = {
                "model": model_name,
                "messages": current_messages,
                "temperature": 0.7,
                "top_p": 1.0,
                "stream": False,
            }

            if tools:
                data["tools"] = tools
                data["tool_choice"] = "auto"

            try:
                response = requests.post(url, headers=headers, json=data, timeout=60)

                if response.status_code != 200:
                    error_msg = f"Skywork Router API error: status={response.status_code}"
                    yield {"type": "error", "content": error_msg}
                    break

                resp_json = response.json()

                if "choices" not in resp_json or len(resp_json["choices"]) == 0:
                    yield {"type": "error", "content": "Empty choices in response"}
                    break

                choice = resp_json["choices"][0]
                message = choice.get("message", {})
                content = message.get("content", "")
                tool_calls_data = message.get("tool_calls", [])

                if content:
                    chunk_size = 10
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i : i + chunk_size]
                        yield {"type": "text", "content": chunk}
                        await asyncio.sleep(0.01)

                if not tool_calls_data:
                    break

                assistant_message = {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": tool_calls_data,
                }
                current_messages.append(assistant_message)

                for tool_call in tool_calls_data:
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]

                    try:
                        tool_args = json.loads(tool_args_str)
                    except json.JSONDecodeError:
                        tool_args = {}

                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "args": tool_args,
                    }

                    try:
                        result = await self._execute_tool(tool_name, tool_args)
                        result_str = self._serialize_tool_result(result)
                    except Exception as e:
                        result_str = f"Error executing tool: {str(e)}"

                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": result_str,
                    }

                    current_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result_str,
                        }
                    )

            except requests.exceptions.Timeout:
                yield {"type": "error", "content": "API timeout"}
                break
            except Exception as e:
                yield {"type": "error", "content": f"Error: {str(e)}"}
                break

        if iteration >= max_iterations:
            yield {
                "type": "text",
                "content": "\n\n[Reached maximum tool calling iterations]",
            }

        conversation_messages = [msg for msg in current_messages if msg.get("role") != "system"]
        yield {"type": "done", "messages": conversation_messages}

    async def _generate_gemini_stream(
        self,
        api_key: str,
        model_name: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_iterations: int,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming response using Gemini."""
        try:
            from google import genai  # type: ignore
        except ImportError as e:
            yield {"type": "error", "content": f"Gemini SDK not installed: {str(e)}"}
            return

        os.environ["GOOGLE_API_KEY"] = api_key
        client = genai.Client()

        prompt = self._messages_to_gemini_prompt(messages)

        try:
            response = client.models.generate_content_stream(
                model=model_name,
                contents=prompt,
                config={"temperature": 0.7},
            )

            for chunk in response:
                if chunk.text:
                    yield {"type": "text", "content": chunk.text}

            conversation_messages = [msg for msg in messages if msg.get("role") != "system"]
            yield {"type": "done", "messages": conversation_messages}

        except Exception as e:
            yield {"type": "error", "content": f"Gemini error: {str(e)}"}

    def _messages_to_gemini_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Convert messages to Gemini prompt."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"[System]\n{content}\n")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        return "\n".join(parts)

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Execute a tool (filesystem or MCP)."""
        # Handle filesystem tools
        if tool_name == "read_file":
            return await self._read_file(tool_args.get("path", ""))
        elif tool_name == "list_directory":
            return await self._list_directory(tool_args.get("path", ""))

        # Handle MCP tools
        if self.mcp_client:
            try:
                result = await self.mcp_client.call_tool(tool_name, tool_args)
                return result
            except Exception as e:
                return {"error": f"MCP tool failed: {str(e)}"}

        return {"error": f"Tool '{tool_name}' not found"}

    async def _read_file(self, path: str) -> Dict[str, Any]:
        """Read a file (for loading SKILL.md)."""
        try:
            # Handle relative paths from skills directory
            if not os.path.isabs(path):
                if self.skill_manager:
                    path = os.path.join(self.skill_manager.skills_root, path)
            
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            return {
                "success": True,
                "path": path,
                "content": content
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {str(e)}"
            }

    async def _list_directory(self, path: str) -> Dict[str, Any]:
        """List directory contents."""
        try:
            if not os.path.isabs(path):
                if self.skill_manager:
                    path = os.path.join(self.skill_manager.skills_root, path)
            
            entries = os.listdir(path)
            
            return {
                "success": True,
                "path": path,
                "entries": entries
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list directory: {str(e)}"
            }

    def _serialize_tool_result(self, result: Any) -> str:
        """Serialize tool result to JSON."""
        normalized = result
        if hasattr(result, "structuredContent"):
            normalized = result.structuredContent
        elif hasattr(result, "content"):
            normalized = result.content

        try:
            return json.dumps(normalized, ensure_ascii=False, default=str)
        except Exception:
            return json.dumps({"result": str(normalized)}, ensure_ascii=False)
