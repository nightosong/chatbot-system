"""
Code Service - OpenCode-inspired development agent
Provides file operations, bash execution, and code intelligence

Supported LLM Providers:
- Gemini (Google Generative AI)
- OpenAI (GPT-3.5, GPT-4, GPT-4o, etc.)
- DeepSeek (deepseek-chat, deepseek-coder)
- Kimi (Moonshot AI)
- QWen (Alibaba Tongyi Qianwen)
- Skywork Router (with special app_key authentication)
- Any OpenAI-compatible API providers

The service automatically routes to the appropriate LLM handler based on the provider field.
"""

import os
import subprocess
import asyncio
import glob as glob_module
import re
import json
from typing import Optional, Dict, Any, AsyncGenerator, List
from pathlib import Path

from services.permission_service import PermissionService


class CodeService:
    """Service for code development mode with tool calling"""

    def __init__(self, workspace_root: str | None = None, llm_service=None):
        """
        Initialize Code Service

        Args:
            workspace_root: Root directory for file operations (default: cwd)
            llm_service: LLM service instance for AI responses
        """
        self.workspace_root = workspace_root or os.getcwd()
        self.permission_service = PermissionService()
        self.llm_service = llm_service

        # Ensure workspace root exists and is absolute
        self.workspace_root = os.path.abspath(self.workspace_root)
        if not os.path.exists(self.workspace_root):
            raise ValueError(f"Workspace root does not exist: {self.workspace_root}")

    async def generate_code_stream(
        self,
        message: str,
        conversation_history: Optional[List[dict]] = None,
        model_config: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
        max_iterations: int = 20,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate streaming code agent response with tool calling

        Args:
            message: User message
            conversation_history: Previous conversation messages
            model_config: LLM configuration
            language: Response language preference
            max_iterations: Maximum tool calling iterations

        Yields:
            Dict with type and content:
            - {"type": "text", "content": "..."}
            - {"type": "tool_call", "tool": "...", "args": {...}}
            - {"type": "tool_result", "tool": "...", "result": {...}}
            - {"type": "thinking", "content": "..."}
            - {"type": "error", "content": "..."}
            - {"type": "permission_required", "tool": "...", "target": "..."}
            - {"type": "done"}
        """
        if conversation_history is None:
            conversation_history = []

        try:
            # Validate model config
            if not model_config:
                raise ValueError("Model configuration is required for code mode")

            # Build system prompt for code mode
            system_prompt = self._build_code_system_prompt()

            # Get available tools
            tools = self._get_code_tools()

            # Import LLM service dynamically to avoid circular imports
            if self.llm_service is None:
                from services.llm_service import LLMService

                self.llm_service = LLMService()

            # Build conversation context
            messages = self._build_context(message, conversation_history, system_prompt)

            # Tool calling loop
            iteration = 0
            provider = model_config.get("provider", "").lower()

            while iteration < max_iterations:
                iteration += 1

                # Call LLM with tools based on provider
                if provider == "gemini":
                    response = await self._call_gemini_with_tools(
                        messages, tools, model_config
                    )
                elif provider == "skywork_router":
                    # Skywork Router uses special authentication
                    response = await self._call_skywork_router_with_tools(
                        messages, tools, model_config
                    )
                else:
                    # OpenAI-compatible providers (openai, deepseek, kimi, qwen, etc.)
                    response = await self._call_openai_with_tools(
                        messages, tools, model_config
                    )

                # Check if LLM wants to call tools
                if "tool_calls" in response and response["tool_calls"]:
                    # Execute tool calls
                    for tool_call in response["tool_calls"]:
                        tool_name = tool_call.get("name")
                        tool_args = tool_call.get("arguments", {})

                        # Yield tool call event
                        yield {
                            "type": "tool_call",
                            "tool": tool_name,
                            "args": tool_args,
                        }

                        # Execute tool with progress (bash only for Phase 1)
                        tool_result = None
                        if tool_name == "bash":
                            # Use progress-aware execution for bash
                            async for (
                                progress_event
                            ) in self._execute_bash_with_progress(tool_args):
                                if progress_event.get("type") == "progress":
                                    # Yield progress update
                                    yield {
                                        "type": "tool_progress",
                                        "tool": tool_name,
                                        "message": progress_event.get("message"),
                                    }
                                elif progress_event.get("type") == "result":
                                    tool_result = progress_event.get("result")
                        else:
                            # Standard execution for other tools
                            tool_result = await self._execute_tool(tool_name, tool_args)

                        # Check if permission is required
                        if tool_result and tool_result.get("permission_required"):
                            yield {
                                "type": "permission_required",
                                "tool": tool_name,
                                "target": tool_result.get("target"),
                                "action": tool_result.get("action"),
                            }
                            # For now, deny if permission required
                            # TODO: Implement user confirmation flow
                            tool_result = {
                                "error": "Permission denied - user confirmation required"
                            }

                        # Yield tool result event
                        yield {
                            "type": "tool_result",
                            "tool": tool_name,
                            "result": tool_result,
                        }

                        # Append tool result to messages
                        messages.append(
                            {
                                "role": "assistant",
                                "content": f"Called {tool_name} with args: {tool_args}",
                            }
                        )
                        messages.append(
                            {"role": "user", "content": f"Tool result: {tool_result}"}
                        )

                    # Continue loop to get next response
                    continue

                # No tool calls - stream final text response
                text_content = response.get("content", "")

                # Stream text word by word
                words = text_content.split()
                for i, word in enumerate(words):
                    yield {
                        "type": "text",
                        "content": word + (" " if i < len(words) - 1 else ""),
                    }

                # Exit loop
                break

            # Done
            yield {"type": "done"}

        except Exception as e:
            yield {"type": "error", "content": str(e)}
            yield {"type": "done"}

    def _build_code_system_prompt(self) -> str:
        """Build system prompt for code mode"""
        return f"""You are an AI coding assistant with access to file operations and bash commands.

Current workspace: {self.workspace_root}

Available tools:
- read: Read file contents (supports pagination)
- write: Create or overwrite files
- edit: Make exact string replacements in files
- bash: Execute shell commands (requires user approval for dangerous commands)
- glob: Find files matching patterns
- grep: Search file contents with regex

Guidelines:
1. Always use relative paths within the workspace
2. Use read before edit to see current content
3. For edit, make sure old_string is unique in the file
4. Bash commands may require user confirmation
5. Think step by step when modifying code
6. Test changes when possible

Remember: You can see and modify files, run commands, but always prioritize safety and user intent."""

    def _build_context(
        self, message: str, history: List[dict], system_prompt: str
    ) -> List[dict]:
        """Build conversation context with system prompt"""
        messages = [{"role": "system", "content": system_prompt}]

        # Add history (last 10 turns)
        for msg in history[-20:]:  # 20 messages = 10 turns
            messages.append(msg)

        # Add current message
        messages.append({"role": "user", "content": message})

        return messages

    def _get_code_tools(self) -> List[dict]:
        """Get OpenCode-style tool definitions"""
        return [
            self._tool_read(),
            self._tool_write(),
            self._tool_edit(),
            self._tool_bash(),
            self._tool_glob(),
            self._tool_grep(),
        ]

    # Tool definitions below (will be implemented in next steps)

    def _tool_read(self) -> dict:
        """Read file tool definition"""
        return {
            "type": "function",
            "function": {
                "name": "read",
                "description": "Read contents of a file with line numbers. Supports pagination for large files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to file relative to workspace root",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Line number to start reading from (0-indexed, optional)",
                            "default": 0,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of lines to read (optional, max 2000)",
                            "default": 2000,
                        },
                    },
                    "required": ["file_path"],
                },
            },
        }

    def _tool_write(self) -> dict:
        """Write file tool definition"""
        return {
            "type": "function",
            "function": {
                "name": "write",
                "description": "Create a new file or completely overwrite an existing file. Use edit for partial modifications.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to file relative to workspace root",
                        },
                        "content": {
                            "type": "string",
                            "description": "Complete file content to write",
                        },
                    },
                    "required": ["file_path", "content"],
                },
            },
        }

    def _tool_edit(self) -> dict:
        """Edit file tool definition"""
        return {
            "type": "function",
            "function": {
                "name": "edit",
                "description": "Perform exact string replacement in a file. The old_string must match exactly (including whitespace and indentation). If there are multiple matches, make old_string more specific.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to file relative to workspace root",
                        },
                        "old_string": {
                            "type": "string",
                            "description": "Exact string to replace (must be unique in file)",
                        },
                        "new_string": {
                            "type": "string",
                            "description": "New string to insert",
                        },
                    },
                    "required": ["file_path", "old_string", "new_string"],
                },
            },
        }

    def _tool_bash(self) -> dict:
        """Bash execution tool definition"""
        return {
            "type": "function",
            "function": {
                "name": "bash",
                "description": "Execute a bash command in the workspace directory. Use for testing, building, running scripts. Dangerous commands require user approval.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Bash command to execute",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 30, max: 300)",
                            "default": 30,
                        },
                    },
                    "required": ["command"],
                },
            },
        }

    def _tool_glob(self) -> dict:
        """File pattern matching tool definition"""
        return {
            "type": "function",
            "function": {
                "name": "glob",
                "description": "Find files matching a glob pattern. Supports ** for recursive search (e.g., '**/*.py', 'src/**/*.tsx').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern (e.g., '*.py', '**/*.tsx', 'src/**')",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        }

    def _tool_grep(self) -> dict:
        """Content search tool definition"""
        return {
            "type": "function",
            "function": {
                "name": "grep",
                "description": "Search for text pattern in files using regex. Returns matching lines with file paths and line numbers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to search for",
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Glob pattern to filter files (optional, default: '*')",
                            "default": "*",
                        },
                        "ignore_case": {
                            "type": "boolean",
                            "description": "Case-insensitive search (default: false)",
                            "default": False,
                        },
                    },
                    "required": ["pattern"],
                },
            },
        }

    async def _execute_tool(self, tool_name: str, args: dict) -> dict:
        """
        Execute a tool with given arguments

        Args:
            tool_name: Name of tool to execute
            args: Tool arguments

        Returns:
            dict: Tool execution result
        """
        tool_methods = {
            "read": self.execute_read,
            "write": self.execute_write,
            "edit": self.execute_edit,
            "bash": self.execute_bash,
            "glob": self.execute_glob,
            "grep": self.execute_grep,
        }

        if tool_name not in tool_methods:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return await tool_methods[tool_name](**args)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    # Tool execution methods
    async def execute_read(
        self, file_path: str, offset: int = 0, limit: int = 2000
    ) -> dict:
        """
        Execute read tool - read file contents with line numbers

        Args:
            file_path: Relative path to file
            offset: Starting line number (0-indexed)
            limit: Maximum lines to read (max 2000)

        Returns:
            dict: {
                "content": str (file content with line numbers),
                "total_lines": int,
                "showing": str (e.g., "1-100 of 500")
            } or {"error": str}
        """
        # Check permission
        action = self.permission_service.check("read", file_path, self.workspace_root)
        if action == "deny":
            return {"error": f"Permission denied: Cannot read {file_path}"}
        if action == "ask":
            return {
                "permission_required": True,
                "target": file_path,
                "action": "read",
            }

        # Resolve full path
        full_path = os.path.join(self.workspace_root, file_path)

        # Security check - ensure path is within workspace
        if not os.path.abspath(full_path).startswith(self.workspace_root):
            return {"error": "Access denied: Path outside workspace"}

        # Check if file exists
        if not os.path.exists(full_path):
            return {"error": f"File not found: {file_path}"}

        if not os.path.isfile(full_path):
            return {"error": f"Not a file: {file_path}"}

        try:
            # Read file with encoding detection
            encodings = ["utf-8", "latin-1", "gbk", "gb2312"]
            content = None

            for encoding in encodings:
                try:
                    with open(full_path, "r", encoding=encoding) as f:
                        lines = f.readlines()
                    content = lines
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                return {"error": "Failed to decode file - unsupported encoding"}

            # Apply pagination
            total_lines = len(content)
            limit = min(limit, 2000)  # Cap at 2000 lines
            end = min(offset + limit, total_lines)
            selected_lines = content[offset:end]

            # Format with line numbers (like cat -n)
            output = ""
            for i, line in enumerate(selected_lines, start=offset + 1):
                # Remove trailing newline, we'll add it back
                line = line.rstrip("\n")
                output += f"{i:6d}\t{line}\n"

            return {
                "content": output,
                "total_lines": total_lines,
                "showing": f"{offset + 1}-{end} of {total_lines}",
                "file_path": file_path,
            }

        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}

    async def execute_write(self, file_path: str, content: str) -> dict:
        """
        Execute write tool - create or overwrite file

        Args:
            file_path: Relative path to file
            content: Complete file content

        Returns:
            dict: {"success": bool, "message": str} or {"error": str}
        """
        # Check permission
        action = self.permission_service.check("write", file_path, self.workspace_root)
        if action == "deny":
            return {"error": f"Permission denied: Cannot write {file_path}"}
        if action == "ask":
            return {
                "permission_required": True,
                "target": file_path,
                "action": "write",
            }

        # Resolve full path
        full_path = os.path.join(self.workspace_root, file_path)

        # Security check
        if not os.path.abspath(full_path).startswith(self.workspace_root):
            return {"error": "Access denied: Path outside workspace"}

        try:
            # Create parent directories if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Write file
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Get file size
            file_size = os.path.getsize(full_path)
            line_count = content.count("\n") + (
                1 if content and not content.endswith("\n") else 0
            )

            return {
                "success": True,
                "message": f"Wrote {file_path} ({line_count} lines, {file_size} bytes)",
                "file_path": file_path,
                "lines": line_count,
                "bytes": file_size,
            }

        except Exception as e:
            return {"error": f"Failed to write file: {str(e)}"}

    async def execute_edit(
        self, file_path: str, old_string: str, new_string: str
    ) -> dict:
        """
        Execute edit tool - exact string replacement

        Args:
            file_path: Relative path to file
            old_string: Exact string to replace (must be unique)
            new_string: Replacement string

        Returns:
            dict: {"success": bool, "message": str} or {"error": str}
        """
        # Check permission
        action = self.permission_service.check("edit", file_path, self.workspace_root)
        if action == "deny":
            return {"error": f"Permission denied: Cannot edit {file_path}"}
        if action == "ask":
            return {
                "permission_required": True,
                "target": file_path,
                "action": "edit",
            }

        # Resolve full path
        full_path = os.path.join(self.workspace_root, file_path)

        # Security check
        if not os.path.abspath(full_path).startswith(self.workspace_root):
            return {"error": "Access denied: Path outside workspace"}

        # Check if file exists
        if not os.path.exists(full_path):
            return {"error": f"File not found: {file_path}"}

        try:
            # Read current content
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if old_string exists
            if old_string not in content:
                return {
                    "error": f"String not found in {file_path}. Make sure old_string matches exactly (including whitespace)."
                }

            # Count occurrences
            count = content.count(old_string)
            if count > 1:
                return {
                    "error": f"Multiple matches found ({count} occurrences). Make old_string more specific to ensure unique match."
                }

            # Perform replacement
            new_content = content.replace(old_string, new_string, 1)

            # Write back
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # Calculate diff
            old_lines = len(old_string.split("\n"))
            new_lines = len(new_string.split("\n"))
            diff = new_lines - old_lines

            return {
                "success": True,
                "message": f"Edited {file_path} (replaced {len(old_string)} chars with {len(new_string)} chars, {diff:+d} lines)",
                "file_path": file_path,
                "old_chars": len(old_string),
                "new_chars": len(new_string),
                "line_diff": diff,
            }

        except Exception as e:
            return {"error": f"Failed to edit file: {str(e)}"}

    async def _execute_bash_with_progress(
        self, args: dict
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute bash command with real-time progress updates

        Args:
            args: Tool arguments dict with 'command' and optional 'timeout'

        Yields:
            Progress events: {"type": "progress", "message": str}
            Final result: {"type": "result", "result": dict}
        """
        command = args.get("command", "")
        timeout = args.get("timeout", 30)

        # Step 1: Permission check
        yield {"type": "progress", "message": "🔒 Checking permissions..."}

        action = self.permission_service.check("bash", command, self.workspace_root)
        if action == "deny":
            yield {
                "type": "result",
                "result": {
                    "error": f"Permission denied: Command blocked for security: {command}"
                },
            }
            return
        if action == "ask":
            yield {
                "type": "result",
                "result": {
                    "permission_required": True,
                    "target": command,
                    "action": "bash",
                },
            }
            return

        # Step 2: Validate timeout
        timeout = min(max(timeout, 1), 300)  # 1-300 seconds
        yield {
            "type": "progress",
            "message": f"⚙️ Executing: {command[:50]}{'...' if len(command) > 50 else ''}",
        }

        try:
            # Execute command asynchronously
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_root,
            )

            yield {
                "type": "progress",
                "message": "⏳ Command running, waiting for output...",
            }

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                yield {
                    "type": "progress",
                    "message": "✅ Command completed, processing output...",
                }

                result = {
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                    "exit_code": process.returncode,
                    "command": command,
                    "success": process.returncode == 0,
                }

                yield {"type": "result", "result": result}

            except asyncio.TimeoutError:
                process.kill()
                yield {
                    "type": "result",
                    "result": {
                        "error": f"Command timed out after {timeout}s",
                        "command": command,
                        "timeout": timeout,
                    },
                }

        except Exception as e:
            yield {
                "type": "result",
                "result": {
                    "error": f"Failed to execute command: {str(e)}",
                    "command": command,
                },
            }

    async def execute_bash(self, command: str, timeout: int = 30) -> dict:
        """
        Execute bash tool - run shell command

        Args:
            command: Bash command to execute
            timeout: Timeout in seconds (max 300)

        Returns:
            dict: {
                "stdout": str,
                "stderr": str,
                "exit_code": int,
                "command": str
            } or {"error": str}
        """
        # Check permission
        action = self.permission_service.check("bash", command, self.workspace_root)
        if action == "deny":
            return {
                "error": f"Permission denied: Command blocked for security: {command}"
            }
        if action == "ask":
            return {
                "permission_required": True,
                "target": command,
                "action": "bash",
            }

        # Validate timeout
        timeout = min(max(timeout, 1), 300)  # 1-300 seconds

        try:
            # Execute command in workspace directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "command": command,
                "success": result.returncode == 0,
            }

        except subprocess.TimeoutExpired:
            return {
                "error": f"Command timed out after {timeout}s",
                "command": command,
                "timeout": timeout,
            }
        except Exception as e:
            return {"error": f"Failed to execute command: {str(e)}", "command": command}

    async def execute_glob(self, pattern: str) -> dict:
        """
        Execute glob tool - find files matching pattern

        Args:
            pattern: Glob pattern (e.g., '*.py', '**/*.tsx')

        Returns:
            dict: {
                "matches": list[str],
                "count": int,
                "pattern": str
            } or {"error": str}
        """
        # Check permission
        action = self.permission_service.check("glob", pattern, self.workspace_root)
        if action == "deny":
            return {"error": f"Permission denied: Cannot glob {pattern}"}

        try:
            # Execute glob from workspace root
            full_pattern = os.path.join(self.workspace_root, pattern)
            matches = glob_module.glob(full_pattern, recursive=True)

            # Make paths relative to workspace
            relative_matches = []
            for match in matches:
                # Only include files (not directories)
                if os.path.isfile(match):
                    rel_path = os.path.relpath(match, self.workspace_root)
                    relative_matches.append(rel_path)

            # Sort for consistent ordering
            relative_matches.sort()

            return {
                "matches": relative_matches,
                "count": len(relative_matches),
                "pattern": pattern,
            }

        except Exception as e:
            return {"error": f"Failed to glob pattern: {str(e)}", "pattern": pattern}

    async def execute_grep(
        self, pattern: str, file_pattern: str = "*", ignore_case: bool = False
    ) -> dict:
        """
        Execute grep tool - search file contents

        Args:
            pattern: Regex pattern to search
            file_pattern: Glob pattern to filter files
            ignore_case: Case-insensitive search

        Returns:
            dict: {
                "matches": list[dict],  # [{file, line_num, line_content, ...}]
                "total_matches": int,
                "files_searched": int
            } or {"error": str}
        """
        # Check permission
        action = self.permission_service.check("grep", pattern, self.workspace_root)
        if action == "deny":
            return {"error": f"Permission denied: Cannot grep {pattern}"}

        try:
            # Compile regex
            regex_flags = re.IGNORECASE if ignore_case else 0
            regex = re.compile(pattern, regex_flags)

            # Find files to search
            full_pattern = os.path.join(self.workspace_root, file_pattern)
            files = glob_module.glob(full_pattern, recursive=True)

            matches = []
            files_searched = 0

            for file_path in files:
                # Only search files (not directories)
                if not os.path.isfile(file_path):
                    continue

                files_searched += 1
                rel_path = os.path.relpath(file_path, self.workspace_root)

                try:
                    # Read file and search
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, start=1):
                            if regex.search(line):
                                matches.append(
                                    {
                                        "file": rel_path,
                                        "line_num": line_num,
                                        "line": line.rstrip("\n"),
                                    }
                                )

                                # Limit matches per request
                                if len(matches) >= 500:
                                    break

                except Exception:
                    # Skip files that can't be read
                    continue

                # Stop if too many matches
                if len(matches) >= 500:
                    break

            return {
                "matches": matches,
                "total_matches": len(matches),
                "files_searched": files_searched,
                "pattern": pattern,
                "truncated": len(matches) >= 500,
            }

        except re.error as e:
            return {"error": f"Invalid regex pattern: {str(e)}", "pattern": pattern}
        except Exception as e:
            return {"error": f"Failed to grep: {str(e)}", "pattern": pattern}

    async def _call_gemini_with_tools(
        self, messages: List[dict], tools: List[dict], model_config: dict
    ) -> dict:
        """
        Call Gemini with tool calling support
        Returns dict with either 'content' or 'tool_calls'
        """
        from google import genai  # type: ignore

        # Validate model_config
        if not model_config:
            return {
                "content": "Error: Model configuration is missing. Please configure a model in settings."
            }

        api_key = model_config.get("api_key")
        model_name = model_config.get("model_name", "gemini-1.5-flash")

        # Validate required fields
        if not api_key:
            return {
                "content": "Error: API key is missing. Please configure your API key in model settings."
            }

        try:
            # Configure Gemini client
            client = genai.Client(api_key=api_key)

            # Convert messages to Gemini format
            gemini_messages = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                gemini_messages.append(
                    {"role": role, "parts": [{"text": msg["content"]}]}
                )

            # Convert tools to Gemini format
            gemini_tools = []
            if tools:
                for tool in tools:
                    if tool.get("type") == "function":
                        func = tool["function"]
                        gemini_tools.append(
                            {
                                "function_declarations": [
                                    {
                                        "name": func["name"],
                                        "description": func.get("description", ""),
                                        "parameters": func.get("parameters", {}),
                                    }
                                ]
                            }
                        )

            # Call Gemini
            config = {"tools": gemini_tools} if gemini_tools else {}
            response = client.models.generate_content(
                model=model_name,
                contents=gemini_messages,
                config=config,
            )

            # Parse response
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]

                # Check for tool calls
                if hasattr(candidate, "content") and hasattr(
                    candidate.content, "parts"
                ):
                    for part in candidate.content.parts:
                        if hasattr(part, "function_call"):
                            # Tool call detected
                            fc = part.function_call
                            return {
                                "tool_calls": [
                                    {
                                        "name": fc.name,
                                        "arguments": (
                                            dict(fc.args) if hasattr(fc, "args") else {}
                                        ),
                                    }
                                ]
                            }

                # Text response
                text = (
                    candidate.content.parts[0].text if candidate.content.parts else ""
                )
                return {"content": text}

            return {"content": "No response from Gemini"}

        except Exception as e:
            import traceback

            return {
                "content": f"Gemini error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            }

    async def _call_skywork_router_with_tools(
        self, messages: List[dict], tools: List[dict], model_config: dict
    ) -> dict:
        """
        Call Skywork Router with tool calling support
        Skywork Router uses OpenAI-compatible API but with app_key authentication
        Returns dict with either 'content' or 'tool_calls'
        """
        import requests

        # Validate model_config
        if not model_config:
            return {
                "content": "Error: Model configuration is missing. Please configure a model in settings."
            }

        api_key = model_config.get("api_key")
        model_name = model_config.get("model_name")

        # Validate required fields
        if not api_key:
            return {
                "content": "Error: API key is missing. Please configure your API key in model settings."
            }
        if not model_name:
            return {
                "content": "Error: Model name is missing. Please configure a model in settings."
            }

        try:
            # Skywork Router endpoint
            url = "https://gpt-us.singularity-ai.com/gpt-proxy/router/chat/completions"

            # Skywork Router uses app_key header instead of Authorization
            headers = {
                "Content-Type": "application/json",
                "app_key": api_key,
            }

            # Prepare API parameters (OpenAI-compatible format)
            data = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.7,
                "stream": False,
            }

            # Add tools if available
            if tools:
                data["tools"] = tools
                data["tool_choice"] = "auto"

            # Call API
            response = requests.post(url, headers=headers, json=data, timeout=60)

            # Check status code
            if response.status_code != 200:
                return {
                    "content": f"Skywork Router API error: status={response.status_code}, body={response.text}"
                }

            # Parse response
            resp_json = response.json()

            # Extract response
            if "choices" not in resp_json or len(resp_json["choices"]) == 0:
                return {"content": "Empty response from Skywork Router"}

            choice = resp_json["choices"][0]
            message_obj = choice.get("message", {})

            # Check for tool calls
            if "tool_calls" in message_obj and message_obj["tool_calls"]:
                tool_calls = []
                for tc in message_obj["tool_calls"]:
                    func = tc.get("function", {})
                    tool_calls.append(
                        {
                            "name": func.get("name"),
                            "arguments": (
                                json.loads(func.get("arguments", "{}"))
                                if isinstance(func.get("arguments"), str)
                                else func.get("arguments", {})
                            ),
                        }
                    )
                return {"tool_calls": tool_calls}

            # Text response
            return {"content": message_obj.get("content", "")}

        except requests.exceptions.Timeout:
            return {"content": "Skywork Router API timeout after 60 seconds"}
        except requests.exceptions.RequestException as e:
            return {"content": f"Skywork Router request failed: {str(e)}"}
        except Exception as e:
            import traceback

            return {
                "content": f"Skywork Router error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            }

    async def _call_openai_with_tools(
        self, messages: List[dict], tools: List[dict], model_config: dict
    ) -> dict:
        """
        Call OpenAI-compatible API with tool calling support
        Returns dict with either 'content' or 'tool_calls'
        """
        from openai import OpenAI

        # Validate model_config
        if not model_config:
            return {
                "content": "Error: Model configuration is missing. Please configure a model in settings."
            }

        api_key = model_config.get("api_key")
        model_name = model_config.get("model_name")
        base_url = model_config.get("base_url")

        # Validate required fields
        if not api_key:
            return {
                "content": "Error: API key is missing. Please configure your API key in model settings."
            }
        if not model_name:
            return {
                "content": "Error: Model name is missing. Please configure a model in settings."
            }

        try:
            # Create OpenAI client
            client = (
                OpenAI(api_key=api_key, base_url=base_url)
                if base_url
                else OpenAI(api_key=api_key)
            )

            # Prepare API parameters
            api_params = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.7,
                "stream": False,  # Non-streaming for simplicity
            }

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = "auto"

            # Call API
            response = client.chat.completions.create(**api_params)

            # Parse response
            choice = response.choices[0]
            message = choice.message

            # Check for tool calls
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_calls = []
                for tc in message.tool_calls:
                    tool_calls.append(
                        {
                            "name": tc.function.name,
                            "arguments": (
                                json.loads(tc.function.arguments)
                                if isinstance(tc.function.arguments, str)
                                else tc.function.arguments
                            ),
                        }
                    )
                return {"tool_calls": tool_calls}

            # Text response
            return {"content": message.content or ""}

        except Exception as e:
            import traceback

            return {
                "content": f"OpenAI error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            }
