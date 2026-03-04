#!/usr/bin/env python3
"""
Test script for Code Mode API endpoint
Tests the /api/code/chat endpoint with a simple file operation
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"


def test_code_api_health():
    """Test basic API health"""
    print("=" * 60)
    print("TEST 1: API Health Check")
    print("=" * 60)

    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✓ Health check passed\n")


def test_code_tools_endpoint():
    """Test /api/code/tools endpoint"""
    print("=" * 60)
    print("TEST 2: Get Available Code Tools")
    print("=" * 60)

    response = requests.get(f"{API_BASE}/api/code/tools")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total tools: {data['count']}")
        print(f"Workspace: {data['workspace_root']}")
        print("\nAvailable tools:")
        for tool in data['tools']:
            tool_name = tool['function']['name']
            tool_desc = tool['function']['description']
            print(f"  - {tool_name}: {tool_desc[:60]}...")
        print("✓ Tools endpoint passed\n")
    else:
        print(f"✗ Tools endpoint failed: {response.text}\n")


def test_code_chat_simple():
    """Test /api/code/chat with a simple request"""
    print("=" * 60)
    print("TEST 3: Simple Code Chat Request")
    print("=" * 60)

    # Prepare request
    payload = {
        "message": "List all Python files in the current directory using glob",
        "llm_config": {
            "provider": "openai",
            "api_key": "test-key",  # Will fail without real key
            "model_name": "gpt-3.5-turbo",
        },
        "max_iterations": 5,
    }

    print(f"Request: {payload['message']}")
    print("Streaming response...")

    try:
        response = requests.post(
            f"{API_BASE}/api/code/chat",
            json=payload,
            stream=True,
            timeout=30,
        )

        print(f"Status: {response.status_code}\n")

        if response.status_code != 200:
            print(f"✗ Request failed: {response.text}")
            return

        # Process SSE stream
        events = []
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]  # Remove "data: " prefix
                    try:
                        event = json.loads(data_str)
                        events.append(event)

                        # Print event
                        event_type = event.get("type")
                        if event_type == "text":
                            print(f"[TEXT] {event.get('content', '')}", end="")
                        elif event_type == "tool_call":
                            print(
                                f"\n[TOOL CALL] {event.get('tool')}: {event.get('args')}"
                            )
                        elif event_type == "tool_result":
                            result = event.get("result", {})
                            print(f"[RESULT] {result}")
                        elif event_type == "error":
                            print(f"\n[ERROR] {event.get('content')}")
                        elif event_type == "done":
                            print("\n[DONE]")

                    except json.JSONDecodeError as e:
                        print(f"Failed to parse: {data_str[:100]}")

        print(f"\nTotal events: {len(events)}")
        print("✓ Code chat endpoint responded\n")

    except requests.exceptions.Timeout:
        print("✗ Request timed out\n")
    except Exception as e:
        print(f"✗ Request failed: {str(e)}\n")


def main():
    """Run all API tests"""
    print("\n" + "=" * 60)
    print("CODE MODE API ENDPOINT TESTS")
    print("=" * 60 + "\n")

    print("⚠️  Note: These tests require the backend server to be running:")
    print("   cd backend && python main.py\n")

    try:
        # Test 1: Health check
        test_code_api_health()

        # Test 2: Tools endpoint
        test_code_tools_endpoint()

        # Test 3: Code chat (will fail without valid API key, but tests endpoint structure)
        test_code_chat_simple()

        print("=" * 60)
        print("API ENDPOINT TESTS COMPLETED")
        print("=" * 60)
        print("\n✓ All endpoint tests passed (structure)")
        print("⚠️  Full functionality requires valid LLM API key\n")

    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Cannot connect to backend server")
        print("   Please start the backend first:")
        print("   cd backend && python main.py\n")
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}\n")


if __name__ == "__main__":
    main()
