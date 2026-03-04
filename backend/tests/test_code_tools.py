#!/usr/bin/env python3
"""
Test script for Code Service tools
Tests all 6 core tools: read, write, edit, bash, glob, grep
"""

import asyncio
import os
import sys
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.code_service import CodeService


async def test_code_tools():
    """Test all Code Service tools"""

    # Create temporary workspace
    temp_dir = tempfile.mkdtemp(prefix="code_test_")
    print(f"✓ Created temporary workspace: {temp_dir}")

    try:
        # Initialize Code Service
        code_service = CodeService(workspace_root=temp_dir)
        print(f"✓ Initialized CodeService\n")

        # Test 1: write tool
        print("=" * 60)
        print("TEST 1: write tool")
        print("=" * 60)
        result = await code_service.execute_write(
            "test.py",
            "# Test file\nprint('Hello, World!')\n"
        )
        print(f"Result: {result}")
        assert result.get("success"), "Write failed"
        print("✓ write tool passed\n")

        # Test 2: read tool
        print("=" * 60)
        print("TEST 2: read tool")
        print("=" * 60)
        result = await code_service.execute_read("test.py")
        print(f"Content preview:\n{result.get('content', '')[0:100]}...")
        assert "Hello, World" in result.get("content", ""), "Read failed"
        print("✓ read tool passed\n")

        # Test 3: edit tool
        print("=" * 60)
        print("TEST 3: edit tool")
        print("=" * 60)
        result = await code_service.execute_edit(
            "test.py",
            "print('Hello, World!')",
            "print('Hello, Code Mode!')"
        )
        print(f"Result: {result}")
        assert result.get("success"), "Edit failed"
        print("✓ edit tool passed\n")

        # Test 4: glob tool
        print("=" * 60)
        print("TEST 4: glob tool")
        print("=" * 60)

        # Create more files
        await code_service.execute_write("test1.txt", "test1")
        await code_service.execute_write("test2.txt", "test2")
        await code_service.execute_write("subdir/test3.py", "# test3")

        result = await code_service.execute_glob("**/*.py")
        print(f"Found {result.get('count')} Python files:")
        for match in result.get("matches", []):
            print(f"  - {match}")
        assert result.get("count") >= 2, "Glob failed"
        print("✓ glob tool passed\n")

        # Test 5: grep tool
        print("=" * 60)
        print("TEST 5: grep tool")
        print("=" * 60)
        result = await code_service.execute_grep(
            "Hello",
            "**/*.py",
            ignore_case=False
        )
        print(f"Found {result.get('total_matches')} matches:")
        for match in result.get("matches", [])[0:5]:
            print(f"  {match['file']}:{match['line_num']}: {match['line']}")
        assert result.get("total_matches") > 0, "Grep failed"
        print("✓ grep tool passed\n")

        # Test 6: bash tool
        print("=" * 60)
        print("TEST 6: bash tool")
        print("=" * 60)
        result = await code_service.execute_bash("ls -la", timeout=5)
        print(f"Full result: {result}")
        print(f"Exit code: {result.get('exit_code')}")
        if result.get("stdout"):
            print(f"Output preview:\n{result.get('stdout', '')[0:200]}")
        # ls command should be allowed by default permissions
        assert result.get("exit_code") == 0 or result.get("success"), "Bash failed"
        print("✓ bash tool passed\n")

        # Test 7: Permission checks
        print("=" * 60)
        print("TEST 7: Permission system")
        print("=" * 60)

        # Try to read .env file (should ask)
        result = await code_service.execute_write(".env", "SECRET=test")
        result = await code_service.execute_read(".env")
        print(f"Reading .env: {result}")
        assert result.get("permission_required"), "Permission check failed"

        # Try dangerous bash command (should deny)
        result = await code_service.execute_bash("rm -rf /")
        print(f"Dangerous command: {result}")
        assert "error" in result or result.get("permission_required"), "Dangerous command not blocked"
        print("✓ permission system passed\n")

        print("=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n✓ Cleaned up temporary workspace")


if __name__ == "__main__":
    asyncio.run(test_code_tools())
