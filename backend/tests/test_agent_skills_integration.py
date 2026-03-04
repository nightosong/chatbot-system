import pytest

from services.agent_service import AgentService
from services.skill_manager import SkillManager


def test_skill_manager_registers_builtin_skills(tmp_path):
    manager = SkillManager(workspace_root=str(tmp_path))
    names = set(manager.list_skill_names())
    assert {"read_file", "write_file", "execute_code", "analyze_data"}.issubset(names)


@pytest.mark.asyncio
async def test_skill_argument_validation_returns_error(tmp_path):
    manager = SkillManager(workspace_root=str(tmp_path))
    result = await manager.execute_skill("write_file", {"file_path": "demo.txt"})
    assert "error" in result
    assert result["error"] == "Invalid skill arguments"
    assert any("content" in item for item in result["validation_errors"])


@pytest.mark.asyncio
async def test_file_skill_respects_workspace_root(tmp_path):
    manager = SkillManager(workspace_root=str(tmp_path))
    result = await manager.execute_skill(
        "write_file",
        {"file_path": "../outside.txt", "content": "hello"},
    )
    assert result["success"] is False
    assert "outside workspace root" in result["error"]


@pytest.mark.asyncio
async def test_agent_generate_stream_includes_skills_when_enabled(tmp_path, monkeypatch):
    manager = SkillManager(workspace_root=str(tmp_path))
    service = AgentService(mcp_client=None, skill_manager=manager)
    captured = {"tools": None}

    async def fake_openai_stream(
        api_key,
        model_name,
        base_url,
        messages,
        tools,
        max_iterations,
        mcp_client_override=None,
    ):
        captured["tools"] = tools
        yield {"type": "text", "content": "ok"}

    monkeypatch.setattr(service, "_generate_openai_stream", fake_openai_stream)

    events = [
        event
        async for event in service.generate_stream(
            message="hello",
            model_config={
                "provider": "openai",
                "api_key": "test-key",
                "model_name": "test-model",
            },
            enable_mcp=False,
            enable_skills=True,
        )
    ]

    tool_names = {
        tool.get("function", {}).get("name", "") for tool in (captured["tools"] or [])
    }
    assert "read_file" in tool_names
    assert events[-1]["type"] == "done"
