import socket

from services.skill_manager import SANDBOX_RUNNER_CODE, Skill, SkillManager


def test_sandbox_allows_resolved_ip_for_allowed_host():
    namespace = {"__name__": "sandbox_test"}
    exec(SANDBOX_RUNNER_CODE, namespace)

    sandbox_socket = namespace["socket"]
    block_network = namespace["_block_network"]

    original_getaddrinfo = sandbox_socket.getaddrinfo
    original_create_connection = sandbox_socket.create_connection
    original_socket_class = sandbox_socket.socket

    seen = {"connected_to": None}

    def fake_getaddrinfo(host, *args, **kwargs):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("198.19.3.11", 443),
            )
        ]

    def fake_create_connection(address, *args, **kwargs):
        seen["connected_to"] = address
        return object()

    try:
        sandbox_socket.getaddrinfo = fake_getaddrinfo
        sandbox_socket.create_connection = fake_create_connection
        block_network({"api.deepseek.com"})

        sandbox_socket.getaddrinfo("api.deepseek.com", 443)
        sandbox_socket.create_connection(("198.19.3.11", 443))

        assert seen["connected_to"] == ("198.19.3.11", 443)
    finally:
        sandbox_socket.getaddrinfo = original_getaddrinfo
        sandbox_socket.create_connection = original_create_connection
        sandbox_socket.socket = original_socket_class


def test_sandbox_blocks_unresolved_ip():
    namespace = {"__name__": "sandbox_test"}
    exec(SANDBOX_RUNNER_CODE, namespace)

    sandbox_socket = namespace["socket"]
    block_network = namespace["_block_network"]

    original_getaddrinfo = sandbox_socket.getaddrinfo
    original_create_connection = sandbox_socket.create_connection
    original_socket_class = sandbox_socket.socket

    try:
        block_network({"api.deepseek.com"})

        try:
            sandbox_socket.create_connection(("198.19.3.11", 443))
            assert False, "expected sandbox to block unresolved IP"
        except RuntimeError as exc:
            assert "blocked host: 198.19.3.11" in str(exc)
    finally:
        sandbox_socket.getaddrinfo = original_getaddrinfo
        sandbox_socket.create_connection = original_create_connection
        sandbox_socket.socket = original_socket_class



def test_skill_timeout_prefers_skill_metadata(tmp_path):
    manager = SkillManager(workspace_root=str(tmp_path))
    skill_dir = tmp_path / "timeout-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: timeout-skill
description: test timeout
tools: []
metadata:
  timeout_seconds: "180"
---

test
""",
        encoding="utf-8",
    )

    skill = manager._parse_skill_file(skill_dir / "SKILL.md", {"type": "local"})
    timeout = manager._resolve_skill_timeout(skill, {}, None)
    assert timeout == 180


def test_skill_timeout_defaults_higher_for_llm(tmp_path):
    manager = SkillManager(workspace_root=str(tmp_path))
    skill = Skill(
        name="demo-skill",
        description="desc",
        tools=[],
        content="content",
        directory=tmp_path,
    )

    timeout = manager._resolve_skill_timeout(skill, {}, {"provider": "openai"})
    assert timeout == 120
