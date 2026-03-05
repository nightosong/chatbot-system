#!/usr/bin/env python3
"""
Test script for agent context functionality
Verifies that conversation history and tool calls are preserved correctly
"""
import asyncio
import json
from services.conversation_service import ConversationService


async def test_save_and_load_messages():
    """Test saving and loading complete message history"""
    print("=" * 60)
    print("Testing Message Save/Load with Tool Calls")
    print("=" * 60)

    # Initialize service
    conv_service = ConversationService(db_path="data/test_conversations.db")

    # Simulate a complete conversation with tool calls
    test_messages = [
        {
            "role": "user",
            "content": "请帮我计算 123 * 456"
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "arguments": '{"expression": "123 * 456"}'
                    }
                }
            ]
        },
        {
            "role": "tool",
            "tool_call_id": "call_abc123",
            "content": '{"result": 56088}'
        },
        {
            "role": "assistant",
            "content": "计算结果是 56088"
        }
    ]

    # Save messages
    print("\n1. Saving messages...")
    conversation_id = conv_service.save_messages(
        messages=test_messages,
        title="Test Conversation"
    )
    print(f"   ✓ Saved with conversation_id: {conversation_id}")

    # Load messages
    print("\n2. Loading messages...")
    loaded_messages = conv_service.get_conversation_messages(conversation_id)
    print(f"   ✓ Loaded {len(loaded_messages)} messages")

    # Verify content
    print("\n3. Verifying message content...")
    success = True

    for i, (original, loaded) in enumerate(zip(test_messages, loaded_messages)):
        print(f"\n   Message {i + 1}:")
        print(f"   - Role: {loaded.get('role')}")
        print(f"   - Content: {loaded.get('content')[:50] if loaded.get('content') else 'None'}")

        # Check tool_calls
        if "tool_calls" in original:
            if "tool_calls" in loaded:
                print(f"   - Tool calls: ✓ Present ({len(loaded['tool_calls'])} calls)")
                # Verify structure
                orig_call = original["tool_calls"][0]
                loaded_call = loaded["tool_calls"][0]
                if orig_call["function"]["name"] != loaded_call["function"]["name"]:
                    print(f"   ✗ Tool call name mismatch!")
                    success = False
            else:
                print(f"   ✗ Tool calls: Missing!")
                success = False

        # Check tool_call_id
        if "tool_call_id" in original:
            if "tool_call_id" in loaded:
                print(f"   - Tool call ID: ✓ {loaded['tool_call_id']}")
            else:
                print(f"   ✗ Tool call ID: Missing!")
                success = False

    print("\n" + "=" * 60)
    if success:
        print("✓ ALL TESTS PASSED")
        print("Context functionality is working correctly!")
    else:
        print("✗ SOME TESTS FAILED")
        print("Please check the implementation")
    print("=" * 60)

    return success


async def test_message_building():
    """Test that _build_messages correctly handles history with tool calls"""
    print("\n" + "=" * 60)
    print("Testing Message Building with History")
    print("=" * 60)

    from services.agent_service import AgentService

    # Create agent service
    agent = AgentService()

    # Simulate conversation history with tool calls
    history = [
        {
            "role": "user",
            "content": "计算 10 + 20",
            "timestamp": "2024-01-01T10:00:00"
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "arguments": '{"expression": "10 + 20"}'
                    }
                }
            ],
            "timestamp": "2024-01-01T10:00:01"
        },
        {
            "role": "tool",
            "tool_call_id": "call_123",
            "content": '{"result": 30}',
            "timestamp": "2024-01-01T10:00:02"
        },
        {
            "role": "assistant",
            "content": "结果是 30",
            "timestamp": "2024-01-01T10:00:03"
        }
    ]

    # Build messages
    print("\n1. Building messages with history...")
    messages = agent._build_messages(
        message="刚才的结果是多少？",
        conversation_history=history,
        file_context=None,
        language="zh-CN",
        available_tools=[],
        available_skills=[]
    )

    print(f"   ✓ Built {len(messages)} messages")

    # Verify structure
    print("\n2. Verifying message structure...")
    success = True

    # Should have: system + 4 history messages + 1 new user message = 6 total
    if len(messages) < 5:
        print(f"   ✗ Expected at least 5 messages, got {len(messages)}")
        success = False
    else:
        print(f"   ✓ Message count correct")

    # Check for tool calls in history
    tool_call_found = False
    tool_result_found = False

    for msg in messages:
        if msg.get("role") == "assistant" and "tool_calls" in msg:
            tool_call_found = True
            print(f"   ✓ Found tool call in assistant message")
        if msg.get("role") == "tool" and "tool_call_id" in msg:
            tool_result_found = True
            print(f"   ✓ Found tool result with tool_call_id")

    if not tool_call_found:
        print(f"   ✗ Tool call not found in messages")
        success = False

    if not tool_result_found:
        print(f"   ✗ Tool result not found in messages")
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✓ MESSAGE BUILDING TEST PASSED")
    else:
        print("✗ MESSAGE BUILDING TEST FAILED")
    print("=" * 60)

    return success


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AGENT CONTEXT FIX TEST SUITE")
    print("=" * 60)

    try:
        # Test 1: Save and load messages
        test1_passed = await test_save_and_load_messages()

        # Test 2: Message building
        test2_passed = await test_message_building()

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Save/Load Test: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
        print(f"Message Building Test: {'✓ PASSED' if test2_passed else '✗ FAILED'}")

        if test1_passed and test2_passed:
            print("\n✓ ALL TESTS PASSED")
            print("Agent context functionality has been successfully fixed!")
        else:
            print("\n✗ SOME TESTS FAILED")
            print("Please review the implementation")

        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST EXECUTION FAILED")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
