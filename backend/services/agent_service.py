"""
Agent Service - Handles agent mode with MCP and skill support
Provides streaming responses and tool calling capabilities
"""

import json
import asyncio
import requests
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import OpenAI
from google import genai  # type: ignore


class AgentService:
    """Service for agent mode with streaming, MCP, and skill support"""

    def __init__(self, mcp_client=None, skill_manager=None):
        """
        Initialize Agent Service

        Args:
            mcp_client: MCP client instance for tool calling
            skill_manager: Skill manager instance for custom skills
        """
        self.mcp_client = mcp_client
        self.skill_manager = skill_manager

    async def generate_stream(
        self,
        message: str,
        conversation_history: Optional[List[dict]] = None,
        file_context: Optional[str] = None,
        model_config: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
        enable_mcp: bool = True,
        enable_skills: bool = True,
        max_iterations: int = 10,
        mcp_client_override=None,
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
            - {"type": "done"}
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

            # Get available tools
            tools = []
            # Use override MCP client if provided, otherwise use instance client
            active_mcp_client = (
                mcp_client_override if mcp_client_override else self.mcp_client
            )

            if enable_mcp and active_mcp_client:
                mcp_tools = await active_mcp_client.list_tools()
                tools.extend(mcp_tools)
            # if enable_skills and self.skill_manager:
            #     skill_tools = self.skill_manager.get_tools()
            #     tools.extend(skill_tools)

            # Build messages
            messages = self._build_messages(
                message, conversation_history, file_context, language
            )

            # Route to appropriate provider
            if provider == "gemini":
                async for chunk in self._generate_gemini_stream(
                    api_key,
                    model_name,
                    messages,
                    tools,
                    max_iterations,
                    active_mcp_client,
                ):
                    yield chunk
            elif provider == "skywork_router":
                async for chunk in self._generate_skywork_router_stream(
                    api_key,
                    model_name,
                    messages,
                    tools,
                    max_iterations,
                    active_mcp_client,
                ):
                    yield chunk
            else:
                async for chunk in self._generate_openai_stream(
                    api_key,
                    model_name,
                    base_url,
                    messages,
                    tools,
                    max_iterations,
                    active_mcp_client,
                ):
                    yield chunk

            yield {"type": "done"}

        except Exception as e:
            yield {"type": "error", "content": str(e)}

    def _build_messages(
        self,
        message: str,
        conversation_history: List[dict],
        file_context: Optional[str],
        language: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Build messages for agent mode"""
        messages = []

        # System prompt
        system_content = """You are a helpful AI assistant with access to tools and skills.
When you need to perform actions or get information, you can call available tools.
Think step by step and explain your reasoning when using tools."""

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

        messages.append({"role": "system", "content": system_content})

        # Add history (last 20 messages)
        if conversation_history:
            for msg in conversation_history[-20:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})

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
        mcp_client_override=None,
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
                    result = await self._execute_tool(
                        tool_name, tool_args, mcp_client_override
                    )
                    result_str = json.dumps(result, ensure_ascii=False)
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

    async def _generate_skywork_router_stream(
        self,
        api_key: str,
        model_name: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_iterations: int,
        mcp_client_override=None,
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
                        result = await self._execute_tool(
                            tool_name, tool_args, mcp_client_override
                        )
                        result_str = json.dumps(
                            result.structuredContent, ensure_ascii=False
                        )
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

    async def _generate_gemini_stream(
        self,
        api_key: str,
        model_name: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_iterations: int,
        mcp_client_override=None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming response using Gemini with tool calling"""
        import os

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
        self, tool_name: str, tool_args: Dict[str, Any], mcp_client_override=None
    ) -> Any:
        """Execute a tool by name"""
        # Use override MCP client if provided
        active_mcp_client = (
            mcp_client_override if mcp_client_override else self.mcp_client
        )

        # Try MCP tools first
        if active_mcp_client:
            try:
                result = await active_mcp_client.call_tool(tool_name, tool_args)
                return result
            except Exception:
                pass

        # Try custom skills
        if self.skill_manager:
            try:
                result = await self.skill_manager.execute_skill(tool_name, tool_args)
                return result
            except Exception:
                pass

        # Tool not found
        return {"error": f"Tool '{tool_name}' not found"}
