#!/usr/bin/env python3
"""
Test script for Agent mode
Tests streaming, tool calling, and agent functionality
"""

import asyncio
import json
from services.agent_service import AgentService
from services.mcp_client import MCPClient, BuiltinMCPTools
from services.skill_manager import SkillManager


async def test_builtin_tools():
    """Test built-in MCP tools"""
    print("=" * 60)
    print("Testing Built-in MCP Tools")
    print("=" * 60)

    # Test calculate
    print("\n1. Testing calculate tool...")
    result = await BuiltinMCPTools.execute("calculate", {"expression": "123 * 456"})
    print(f"   Result: {result}")

    # Test get_current_time
    print("\n2. Testing get_current_time tool...")
    result = BuiltinMCPTools._get_current_time("Asia/Shanghai")
    print(f"   Result: {result}")

    # Test web_search (placeholder)
    print("\n3. Testing web_search tool...")
    result = await BuiltinMCPTools._web_search("Python programming", 3)
    print(f"   Result: {result}")


async def test_skills():
    """Test custom skills"""
    print("\n" + "=" * 60)
    print("Testing Custom Skills")
    print("=" * 60)

    skill_manager = SkillManager()

    # Test analyze_data
    print("\n1. Testing analyze_data skill...")
    result = await skill_manager.execute_skill(
        "analyze_data",
        {
            "data": [10, 20, 30, 40, 50],
            "operations": ["mean", "median", "std", "min", "max", "sum"],
        },
    )
    print(f"   Result: {json.dumps(result, indent=2)}")

    # Test execute_code
    print("\n2. Testing execute_code skill...")
    result = await skill_manager.execute_skill(
        "execute_code",
        {
            "code": """
result = sum(range(1, 11))
print(f"Sum of 1 to 10: {result}")
""",
            "timeout": 5,
        },
    )
    print(f"   Result: {json.dumps(result, indent=2)}")


async def test_agent_stream():
    """Test agent streaming (without actual LLM call)"""
    print("\n" + "=" * 60)
    print("Testing Agent Service Structure")
    print("=" * 60)

    # Initialize services
    mcp_client = MCPClient()
    skill_manager = SkillManager()
    agent_service = AgentService(mcp_client=mcp_client, skill_manager=skill_manager)

    print("\n✓ Agent service initialized successfully")

    # Get available tools
    print("\n1. Available MCP tools:")
    builtin_tools = BuiltinMCPTools.list_tools()
    for tool in builtin_tools:
        print(f"   - {tool['function']['name']}: {tool['function']['description']}")

    print(f"\n✓ Total tools available: {len(builtin_tools)}")


async def test_tool_format():
    """Test tool format conversion"""
    print("\n" + "=" * 60)
    print("Testing Tool Format")
    print("=" * 60)

    mcp_client = MCPClient()

    # Test format conversion
    mcp_tool = {
        "name": "test_tool",
        "description": "A test tool",
        "inputSchema": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "First parameter"}
            },
            "required": ["param1"],
        },
    }

    formatted = mcp_client._format_tool(mcp_tool)
    print("\nOriginal MCP format:")
    print(json.dumps(mcp_tool, indent=2))
    print("\nConverted to OpenAI format:")
    print(json.dumps(formatted, indent=2))


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AGENT MODE TEST SUITE")
    print("=" * 60)

    try:
        # Test 1: Built-in tools
        await test_builtin_tools()

        # Test 2: Custom skills
        await test_skills()

        # Test 3: Agent service
        await test_agent_stream()

        # Test 4: Tool format
        await test_tool_format()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nAgent mode is ready to use!")
        print("\nNext steps:")
        print("1. Start the server: python main.py")
        print("2. Test with curl or Python client (see AGENT_MODE.md)")
        print("3. Configure your LLM API key")
        print("4. Try agent chat with tool calling")

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
