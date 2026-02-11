"""
MCP Client - Model Context Protocol client implementation
Provides integration with MCP servers for tool calling
"""

from typing import Any
import mcp.types as types  # type: ignore
from fastmcp.client import Client


class MCPClient:
    """Client for interacting with MCP servers"""

    def __init__(self, servers_config: dict[str, dict[str, Any]] | None = None):
        """
        Initialize MCP Client

        Args:
            servers_config: dict of MCP servers
                {
                    "ServerName": {
                        "url": "...",
                        "transport": "sse",
                    },
                    "_meta": {
                        "user_id": "...",
                        "project_id": "...",
                        "office_id": "...",
                        ...
                    }
                }
        """
        self.servers_config = servers_config or {}
        self.tools_cache: list[dict[str, Any]] | None = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """
        Get available tools from all configured MCP servers

        Returns:
            List of tool definitions in OpenAI function calling format
        """
        # Return cached tools if available
        if self.tools_cache is not None:
            return self.tools_cache

        # If no servers configured, return empty list
        if not self.servers_config:
            return []

        all_tools = []
        # Query each MCP server
        async with Client(self.servers_config) as mcp_client:
            tools = await mcp_client.list_tools()
            tools_schema = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema.get("properties", {}),
                    },
                }
                for tool in tools
            ]
            all_tools.extend(tools_schema)

        # Cache the tools
        self.tools_cache = all_tools
        return all_tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Call a tool on the appropriate MCP server

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if not self.servers_config:
            raise ValueError("No MCP servers configured")

        meta_info = self.servers_config.get("_meta", {})

        async with Client(self.servers_config) as mcp_client:
            response = await mcp_client.session.send_request(
                types.ClientRequest(
                    types.CallToolRequest(
                        method="tools/call",
                        params=types.CallToolRequestParams(
                            name=tool_name,
                            arguments=arguments,
                            _meta=types.RequestParams.Meta(
                                progressToken="123",
                                user_id=meta_info.get("user_id", ""),  # type: ignore
                                project_id=meta_info.get("project_id", ""),  # type: ignore
                                office_id=meta_info.get("office_id", ""),  # type: ignore
                                membership_refactor=True,  # type: ignore
                            ),
                        ),
                    )
                ),
                types.CallToolResult,
            )
            return response

    def _format_tool(self, tool: dict[str, Any]) -> dict[str, Any]:
        """
        Format tool definition to OpenAI function calling format

        Args:
            tool: MCP tool definition

        Returns:
            OpenAI-formatted tool definition
        """
        # If already in correct format, return as is
        if tool.get("type") == "function" and "function" in tool:
            return tool

        # Convert MCP format to OpenAI format
        return {
            "type": "function",
            "function": {
                "name": tool.get("name", "unknown"),
                "description": tool.get("description", ""),
                "parameters": tool.get(
                    "inputSchema",
                    {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
            },
        }

    async def close(self):
        """Close the HTTP client"""

    def clear_cache(self):
        """Clear the tools cache"""
        self.tools_cache = None


# Built-in MCP tools for common operations
class BuiltinMCPTools:
    """Built-in MCP tools that don't require external server"""

    @staticmethod
    def list_tools() -> list[dict[str, Any]]:
        """Get built-in tool definitions"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query",
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "Number of results to return",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Perform mathematical calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Mathematical expression to evaluate",
                            },
                        },
                        "required": ["expression"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "Get current date and time",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "timezone": {
                                "type": "string",
                                "description": "Timezone (e.g., 'UTC', 'Asia/Shanghai')",
                                "default": "UTC",
                            },
                        },
                        "required": [],
                    },
                },
            },
        ]

    @staticmethod
    async def execute(tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a built-in tool"""
        if tool_name == "web_search":
            return await BuiltinMCPTools._web_search(
                arguments.get("query", ""),
                arguments.get("num_results", 5),
            )
        elif tool_name == "calculate":
            return BuiltinMCPTools._calculate(arguments.get("expression", ""))
        elif tool_name == "get_current_time":
            return BuiltinMCPTools._get_current_time(arguments.get("timezone", "UTC"))
        else:
            raise ValueError(f"Unknown built-in tool: {tool_name}")

    @staticmethod
    async def _web_search(query: str, num_results: int) -> dict[str, Any]:
        """Perform web search (placeholder - integrate with actual search API)"""
        # This is a placeholder. In production, integrate with:
        # - Google Custom Search API
        # - Bing Search API
        # - DuckDuckGo API
        # - SerpAPI
        return {
            "query": query,
            "results": [
                {
                    "title": "Search result placeholder",
                    "url": "https://example.com",
                    "snippet": f"This is a placeholder for search results for: {query}",
                }
            ],
            "note": "Web search not implemented. Please configure a search API.",
        }

    @staticmethod
    def _calculate(expression: str) -> dict[str, Any]:
        """Perform safe mathematical calculation"""
        try:
            # Use safe evaluation (only allow basic math operations)
            import ast
            import operator

            # Allowed operations
            operators = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }

            def eval_expr(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    return operators[type(node.op)](
                        eval_expr(node.left), eval_expr(node.right)
                    )
                elif isinstance(node, ast.UnaryOp):
                    return operators[type(node.op)](eval_expr(node.operand))
                else:
                    raise ValueError(f"Unsupported operation: {type(node)}")

            tree = ast.parse(expression, mode="eval")
            result = eval_expr(tree.body)

            return {
                "expression": expression,
                "result": result,
            }
        except Exception as e:
            return {
                "expression": expression,
                "error": str(e),
            }

    @staticmethod
    def _get_current_time(timezone: str) -> dict[str, Any]:
        """Get current time in specified timezone"""
        from datetime import datetime
        import pytz

        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            return {
                "timezone": timezone,
                "datetime": now.isoformat(),
                "formatted": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            }
        except Exception as e:
            # Fallback to UTC
            now = datetime.utcnow()
            return {
                "timezone": "UTC",
                "datetime": now.isoformat(),
                "formatted": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "error": f"Invalid timezone '{timezone}', using UTC",
            }
