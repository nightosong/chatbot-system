"""
Agent Service - Handles agent mode with MCP and skill support
Provides streaming responses and tool calling capabilities
"""

import json
import asyncio
import requests
import os
import threading
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import OpenAI
from services.skill_manager import SkillManager


class AgentService:
    """Service for agent mode with streaming, MCP, and skill support.

    This service is designed to be instantiated per-request to support
    different MCP configurations for each request. The skill_manager
    should be shared across all instances (singleton).
    """

    # Class-level cache for system prompt (shared across all instances)
    _default_system_prompt_cache: Optional[str] = None
    _prompt_cache_lock = threading.Lock()

    def __init__(self, mcp_client=None, skill_manager: SkillManager | None = None):
        """
        Initialize Agent Service (per-request instance)

        Args:
            mcp_client: MCP client instance for tool calling (request-specific)
            skill_manager: Skill manager instance for custom skills (shared singleton)
        """
        self.mcp_client = mcp_client
        self.skill_manager = skill_manager
        # Set during generate_stream so _execute_tool can forward them to skills
        self._current_model_config: Optional[Dict[str, Any]] = None
        self._current_mcp_config: Optional[Dict[str, Any]] = None
        self._default_system_prompt = self._load_default_system_prompt()

    def _load_default_system_prompt(self) -> str:
        """Load default system prompt from prompts/general_agent.md with fallback.

        Uses class-level cache to avoid loading the same file multiple times.
        """
        # Check cache first
        if self._default_system_prompt_cache is not None:
            return self._default_system_prompt_cache

        # Load with lock to avoid race conditions
        with self._prompt_cache_lock:
            # Double-check after acquiring lock
            if self._default_system_prompt_cache is not None:
                return self._default_system_prompt_cache

            prompt_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "prompts",
                "general_agent.md",
            )
            fallback = (
                "You are a helpful AI assistant with access to tools and skills.\n"
                "When you need to perform actions or get information, you can call available tools.\n"
                "Think step by step and explain your reasoning when using tools."
            )

            try:
                with open(prompt_path, "r", encoding="utf-8") as file:
                    content = file.read().strip()
                result = content or fallback
            except Exception:
                result = fallback

            # Cache the result
            self._default_system_prompt_cache = result
            return result

    def _deduplicate_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate tools by function name to avoid model confusion."""
        deduplicated: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for tool in tools:
            function_info = tool.get("function", {})
            name = function_info.get("name")
            if not name or name in seen:
                continue
            seen.add(name)
            deduplicated.append(tool)
        return deduplicated

    def _serialize_tool_result(self, result: Any) -> str:
        """Serialize tool result to JSON string for model and SSE transport."""
        normalized = result
        if hasattr(result, "structuredContent"):
            normalized = result.structuredContent
        elif hasattr(result, "content"):
            normalized = result.content

        try:
            return json.dumps(normalized, ensure_ascii=False, default=str)
        except Exception:
            return json.dumps({"result": str(normalized)}, ensure_ascii=False)

    def _build_capabilities_prompt(
        self,
        tools: List[Dict[str, Any]],
        skills: List[Dict[str, Any]],
    ) -> str:
        """Build capability section with detailed tool and skill metadata.

        This method creates a clear description of available capabilities:
        - MCP Tools: External tools provided by MCP servers
        - Skills: Custom execution units with specific behaviors defined in SKILL.md
        """
        sections: List[str] = []

        # Separate MCP tools and skills based on whether they appear in skills list
        skill_names = {skill.get("name") for skill in skills if skill.get("name")}
        mcp_tools = []
        skill_tools = []

        for tool in tools:
            function_info = tool.get("function", {})
            name = function_info.get("name", "")
            if not name:
                continue

            if name in skill_names:
                skill_tools.append(tool)
            else:
                mcp_tools.append(tool)

        # Build MCP tools section
        if mcp_tools:
            tool_lines: List[str] = []
            for item in mcp_tools:
                function_info = item.get("function", {})
                name = function_info.get("name", "")
                description = function_info.get("description", "")
                parameters = function_info.get("parameters", {})
                tool_lines.append(
                    f"- **{name}**\n"
                    f"  Description: {description}\n"
                    f"  Parameters: {json.dumps(parameters, ensure_ascii=False)}"
                )
            if tool_lines:
                sections.append(
                    "[Available MCP Tools]\n"
                    + "These are external tools provided by MCP servers:\n"
                    + "\n".join(tool_lines)
                )

        # Build skills section with more detail
        if skills:
            skill_lines: List[str] = []
            for skill in skills:
                name = skill.get("name", "")
                description = skill.get("description", "")
                metadata = skill.get("metadata", {})
                if not name:
                    continue

                skill_line = f"- **{name}**\n  Description: {description}"
                if metadata:
                    skill_path = metadata.get("path", "")
                    if skill_path:
                        skill_line += f"\n  Location: {skill_path}"
                skill_lines.append(skill_line)

            if skill_lines:
                sections.append(
                    "[Available Skills]\n"
                    + "These are custom execution units with specific behaviors:\n"
                    + "\n".join(skill_lines)
                    + "\n\nNote: Skills are executed in a sandboxed environment. "
                    + "Pass all required parameters as specified in each skill's description."
                )

        if not sections:
            return ""

        return "\n\n" + "\n\n".join(sections)

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
        max_iterations: int = 10,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate streaming agent response with tool calling support

        Args:
            message: User message
            conversation_history: Conversation history
            file_context: File context
            model_config: Model configuration
            language: Language preference
            enable_mcp: Whether to enable MCP tools
            enable_skills: Whether to enable custom skills
            max_iterations: Maximum tool calling iterations

        Yields:
            Dict with type and content:
            - {"type": "text", "content": "..."}
            - {"type": "tool_call", "tool": "...", "args": {...}}
            - {"type": "tool_result", "tool": "...", "result": "..."}
            - {"type": "thinking", "content": "..."}
            - {"type": "error", "content": "..."}
            - {"type": "done", "messages": [...]}  # Final message includes full conversation
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

            # Store for use in _execute_tool so skills receive LLM + MCP configs
            self._current_model_config = model_config
            # mcp_client.servers_config holds the full mcp_servers dict (including _meta)
            self._current_mcp_config = (
                self.mcp_client.servers_config if self.mcp_client else None
            )

            # Get available tools
            tools = []
            if enable_mcp and self.mcp_client:
                mcp_tools = await self.mcp_client.list_tools()
                tools.extend(mcp_tools)

            skill_summaries: List[Dict[str, Any]] = []
            if enable_skills and self.skill_manager:
                selected_skill_name_set = set(selected_skill_names or [])
                skill_tools = self.skill_manager.get_tools()
                skill_summaries = self.skill_manager.list_skills()

                if selected_skill_name_set:
                    skill_tools = [
                        tool for tool in skill_tools
                        if tool.get("function", {}).get("name") in selected_skill_name_set
                    ]
                    skill_summaries = [
                        skill for skill in skill_summaries
                        if skill.get("name") in selected_skill_name_set
                    ]

                tools.extend(skill_tools)

            tools = self._deduplicate_tools(tools)

            # Build messages
            messages = self._build_messages(
                message,
                conversation_history,
                file_context,
                language,
                tools,
                skill_summaries,
            )

            # Store the final messages (will be updated by provider methods)
            final_messages = []

            # Route to appropriate provider
            if provider == "gemini":
                async for chunk in self._generate_gemini_stream(
                    api_key,
                    model_name,
                    messages,
                    tools,
                    max_iterations,
                ):
                    if chunk.get("type") == "done" and "messages" in chunk:
                        final_messages = chunk["messages"]
                    yield chunk
            elif provider == "skywork_router":
                async for chunk in self._generate_skywork_router_stream(
                    api_key,
                    model_name,
                    messages,
                    tools,
                    max_iterations,
                ):
                    if chunk.get("type") == "done" and "messages" in chunk:
                        final_messages = chunk["messages"]
                    yield chunk
            else:
                async for chunk in self._generate_openai_stream(
                    api_key,
                    model_name,
                    base_url,
                    messages,
                    tools,
                    max_iterations,
                ):
                    if chunk.get("type") == "done" and "messages" in chunk:
                        final_messages = chunk["messages"]
                    yield chunk

            # Return final done message with complete conversation
            yield {"type": "done", "messages": final_messages}

        except Exception as e:
            yield {"type": "error", "content": str(e)}

    def _build_messages(
        self,
        message: str,
        conversation_history: List[dict],
        file_context: Optional[str],
        language: Optional[str],
        available_tools: Optional[List[Dict[str, Any]]] = None,
        available_skills: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Build messages for agent mode"""
        messages = []

        # System prompt
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

        capability_prompt = self._build_capabilities_prompt(
            available_tools or [],
            available_skills or [],
        )
        if capability_prompt:
            system_content += (
                capability_prompt + "\n\nOnly call tools from the available tools list."
            )

        messages.append({"role": "system", "content": system_content})

        # Add history (last 20 messages, excluding system messages)
        # Important: Include tool calls and tool results for proper context
        if conversation_history:
            for msg in conversation_history[-20:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                # Skip system messages from history
                if role == "system":
                    continue

                # Build message with full context
                history_msg = {"role": role, "content": content}

                # Include tool calls if present (for assistant messages)
                if role == "assistant" and "tool_calls" in msg:
                    history_msg["tool_calls"] = msg["tool_calls"]

                # Include tool_call_id if present (for tool messages)
                if role == "tool" and "tool_call_id" in msg:
                    history_msg["tool_call_id"] = msg["tool_call_id"]

                # Only add messages with content or tool calls
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
        """Generate streaming response using OpenAI-compatible API with tool calling"""
        # Initialize client
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        current_messages = messages.copy()
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Prepare API call parameters
            api_params = {
                "model": model_name,
                "messages": current_messages,
                "temperature": 0.7,
                "stream": True,
            }

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = "auto"

            # Call API with streaming
            stream = client.chat.completions.create(**api_params)  # type: ignore

            # Collect response
            full_content = ""
            tool_calls = []
            current_tool_call = None

            for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # Handle content streaming
                if delta.content:
                    full_content += delta.content
                    yield {"type": "text", "content": delta.content}

                # Handle tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index is not None:
                            # New tool call
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

                            # Update tool call
                            if tc.function:
                                if tc.function.name:
                                    current_tool_call["function"][
                                        "name"
                                    ] = tc.function.name
                                if tc.function.arguments:
                                    current_tool_call["function"][
                                        "arguments"
                                    ] += tc.function.arguments

            # Add last tool call if exists
            if current_tool_call:
                tool_calls.append(current_tool_call)

            # If no tool calls, we're done
            if not tool_calls:
                break

            # Execute tool calls
            assistant_message = {
                "role": "assistant",
                "content": full_content or None,
                "tool_calls": tool_calls,
            }
            current_messages.append(assistant_message)

            # Execute each tool call
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

                # Execute tool
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

                # Add tool result to messages
                current_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result_str,
                    }
                )

        # If we hit max iterations, yield a warning
        if iteration >= max_iterations:
            yield {
                "type": "text",
                "content": "\n\n[Reached maximum tool calling iterations]",
            }

        # Return done with final messages (excluding system message for conversation history)
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
        """Generate streaming response using Skywork Router with tool calling"""
        import requests

        url = "https://gpt-us.singularity-ai.com/gpt-proxy/router/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "app_key": api_key,
        }

        current_messages = messages.copy()
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Build request data
            data = {
                "model": model_name,
                "messages": current_messages,
                "temperature": 0.7,
                "top_p": 1.0,
                "stream": False,  # Skywork Router 使用同步调用
            }

            # Add tools if available
            if tools:
                data["tools"] = tools
                data["tool_choice"] = "auto"

            try:
                # Call API
                response = requests.post(url, headers=headers, json=data, timeout=60)

                if response.status_code != 200:
                    error_msg = f"Skywork Router API error: status={response.status_code}, body={response.text}"
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

                # 模拟流式输出文本内容
                if content:
                    # 按字符或词组分块输出，模拟流式效果
                    chunk_size = 10  # 每次输出10个字符
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i : i + chunk_size]
                        yield {"type": "text", "content": chunk}
                        # 添加小延迟以模拟流式效果
                        await asyncio.sleep(0.01)

                # If no tool calls, we're done
                if not tool_calls_data:
                    break

                # Process tool calls
                assistant_message = {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": tool_calls_data,
                }
                current_messages.append(assistant_message)

                # Execute each tool call
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

                    # Execute tool
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

                    # Add tool result to messages
                    current_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result_str,
                        }
                    )

            except requests.exceptions.Timeout:
                yield {
                    "type": "error",
                    "content": "Skywork Router API timeout after 60 seconds",
                }
                break
            except requests.exceptions.RequestException as e:
                yield {
                    "type": "error",
                    "content": f"Skywork Router API request failed: {str(e)}",
                }
                break
            except Exception as e:
                yield {"type": "error", "content": f"Unexpected error: {str(e)}"}
                break

        # If we hit max iterations, yield a warning
        if iteration >= max_iterations:
            yield {
                "type": "text",
                "content": "\n\n[Reached maximum tool calling iterations]",
            }

        # Return done with final messages (excluding system message for conversation history)
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
        """Generate streaming response using Gemini with tool calling"""
        import os

        try:
            from google import genai  # type: ignore
        except ImportError as e:
            yield {
                "type": "error",
                "content": f"Gemini SDK is not installed: {str(e)}",
            }
            return

        os.environ["GOOGLE_API_KEY"] = api_key
        client = genai.Client()

        # Convert messages to Gemini format
        prompt = self._messages_to_gemini_prompt(messages)

        # Convert tools to Gemini format if needed
        gemini_tools = self._convert_tools_to_gemini(tools) if tools else None

        # Generate with streaming
        try:
            response = client.models.generate_content_stream(
                model=model_name,
                contents=prompt,
                config={"temperature": 0.7},
            )

            for chunk in response:
                if chunk.text:
                    yield {"type": "text", "content": chunk.text}

            # Return done with messages
            conversation_messages = [msg for msg in messages if msg.get("role") != "system"]
            yield {"type": "done", "messages": conversation_messages}

        except Exception as e:
            yield {"type": "error", "content": f"Gemini error: {str(e)}"}

    def _messages_to_gemini_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Convert OpenAI-style messages to Gemini prompt"""
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

    def _convert_tools_to_gemini(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert OpenAI-style tools to Gemini format"""
        # Gemini tool format is different, this is a placeholder
        # In practice, you might need to adapt based on Gemini's actual tool calling API
        return tools

    async def _execute_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Any:
        """Execute a tool by name.

        This method tries to execute the tool in the following order:
        1. Check if it's a custom skill (via skill_manager)
        2. Check if it's an MCP tool (via mcp_client)
        3. Return error if not found

        Skills take priority because they are explicitly loaded and have
        more specific behavior than generic MCP tools.
        """
        # Try custom skills first (skills have priority)
        if self.skill_manager and self.skill_manager.has_skill(tool_name):
            try:
                # Execute skill with the provided arguments.
                # Pass current model_config so skills can make LLM calls internally.
                result = await self.skill_manager.execute_skill(
                    tool_name,
                    tool_args,
                    llm_config=self._current_model_config,
                    mcp_config=self._current_mcp_config,
                )
                return result
            except Exception as e:
                # If skill execution fails, return detailed error
                return {
                    "error": f"Skill '{tool_name}' execution failed: {str(e)}",
                    "skill": tool_name,
                    "type": "skill_error",
                }

        # Try MCP tools
        if self.mcp_client:
            try:
                result = await self.mcp_client.call_tool(tool_name, tool_args)
                return result
            except Exception as e:
                # MCP tool failed, but maybe it doesn't exist
                # Continue to the final error handling
                pass

        # Tool not found in either skills or MCP tools
        return {
            "error": f"Tool '{tool_name}' not found in skills or MCP tools",
            "tool_name": tool_name,
            "available_skills": (
                self.skill_manager.list_skill_names() if self.skill_manager else []
            ),
        }
