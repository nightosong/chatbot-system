import pytest  # type: ignore

from services.agent_service import AgentService
from services.skill_manager import SkillManager


@pytest.fixture(autouse=True)
def reset_skill_manager_singletons():
    """Reset SkillManager singletons before each test to ensure isolation"""
    yield
    SkillManager.reset_instances()


def _write_skill(
    root, folder_name: str, skill_name: str, description: str, script_body: str
):
    skill_dir = root / folder_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: {skill_name}
description: {description}
tools: []
---

{description}
""".strip(),
        encoding="utf-8",
    )
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "run.py").write_text(script_body.strip(), encoding="utf-8")
    return skill_dir


@pytest.mark.asyncio
async def test_skill_manager_starts_without_builtin_skills(tmp_path):
    manager = SkillManager(workspace_root=str(tmp_path))
    assert manager.list_skill_names() == []


@pytest.mark.asyncio
async def test_dynamic_skill_loading_from_local_path(tmp_path):
    manager = SkillManager(workspace_root=str(tmp_path))
    custom_root = tmp_path / "custom_skills"
    _write_skill(
        custom_root,
        "demo-skill",
        "demo-skill",
        "Return greeting from scripts/run.py",
        """
def run(arguments, context):
    name = arguments.get("name", "world")
    return {"message": f"hello, {name}", "skill_dir": context.get("skill_dir")}
""",
    )

    result = await manager.load_skills_from_source(str(custom_root))
    assert result["loaded_count"] == 1
    assert result["loaded_skills"] == ["demo-skill"]
    assert "demo-skill" in manager.list_skill_names()

    exec_result = await manager.execute_skill("demo-skill", {"name": "agent"})
    assert exec_result["success"] is True
    assert exec_result["result"]["message"] == "hello, agent"


@pytest.mark.asyncio
async def test_dynamic_skill_requires_skill_md(tmp_path):
    manager = SkillManager(workspace_root=str(tmp_path))
    invalid_dir = tmp_path / "invalid-skill"
    invalid_dir.mkdir()
    (invalid_dir / "scripts").mkdir()
    (invalid_dir / "scripts" / "run.py").write_text(
        "def run(arguments, context): return {}",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="SKILL.md"):
        await manager.load_skills_from_source(str(invalid_dir))


@pytest.mark.asyncio
async def test_dynamic_skill_load_does_not_execute_script(tmp_path):
    manager = SkillManager(workspace_root=str(tmp_path))
    custom_root = tmp_path / "custom_skills"
    marker = tmp_path / "executed.txt"
    _write_skill(
        custom_root,
        "safe-skill",
        "safe-skill",
        "Only execute on demand",
        f"""
from pathlib import Path

def run(arguments, context):
    Path(r"{marker}").write_text("executed", encoding="utf-8")
    return {{"ok": True}}
""",
    )

    await manager.load_skills_from_source(str(custom_root))
    assert not marker.exists()

    exec_result = await manager.execute_skill("safe-skill", {})
    assert exec_result["success"] is True
    assert marker.exists()
    assert exec_result["result"]["ok"] is True


@pytest.mark.asyncio
async def test_agent_generate_stream_includes_dynamic_skills_when_enabled(
    tmp_path, monkeypatch
):
    manager = SkillManager(workspace_root=str(tmp_path))
    custom_root = tmp_path / "custom_skills"
    _write_skill(
        custom_root,
        "demo-skill",
        "demo-skill",
        "Return greeting from scripts/run.py",
        """
def run(arguments, context):
    return {"message": "ok"}
""",
    )
    await manager.load_skills_from_source(str(custom_root))

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
    assert "demo-skill" in tool_names
    assert events[-1]["type"] == "done"
