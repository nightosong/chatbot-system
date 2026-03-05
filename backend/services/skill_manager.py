"""
Skill Manager for Agent Skills.

Key principles:
- Skills are discovered from SKILL.md files.
- Loading a skill only parses metadata/content; no code executes during load.
- Skill execution happens on demand in a subprocess sandbox.

This implementation borrows the metadata-first Skill/SkillManager design from
`oh-my-agent/skills/skill_manager.py`, adapted to this backend.
"""

import asyncio
import ast
import json
import os
import re
import subprocess
import threading
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


SANDBOX_RUNNER_CODE = textwrap.dedent(
    """
    import asyncio
    import importlib.util
    import inspect
    import json
    import os
    import socket
    import sys


    def _json_safe(value):
        try:
            json.dumps(value)
            return value
        except Exception:
            return str(value)


    def _block_network():
        def _raise(*args, **kwargs):
            raise RuntimeError("Network access is disabled in skill sandbox")

        socket.create_connection = _raise
        socket.getaddrinfo = _raise

        class _BlockedSocket:
            def __init__(self, *args, **kwargs):
                _raise()

        socket.socket = _BlockedSocket


    def _load_module(module_path, module_name):
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if not spec or not spec.loader:
            raise RuntimeError(f"Failed to load module: {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


    async def _call_entrypoint(func, arguments, context):
        params_count = len(inspect.signature(func).parameters)

        if params_count <= 0:
            result = func()
        elif params_count == 1:
            result = func(arguments)
        else:
            result = func(arguments, context)

        if inspect.isawaitable(result):
            return await result
        return result


    def _find_script(scripts_dir):
        if not scripts_dir or not os.path.isdir(scripts_dir):
            return None
        for name in ("run.py", "main.py", "skill.py"):
            candidate = os.path.join(scripts_dir, name)
            if os.path.isfile(candidate):
                return candidate
        return None


    async def _main():
        payload = json.loads(sys.argv[1])
        arguments = payload.get("arguments", {})
        scripts_dir = payload.get("scripts_dir")

        _block_network()

        context = {
            "skill_dir": payload.get("skill_dir"),
            "instruction": payload.get("instruction", ""),
            "references_dir": payload.get("references_dir"),
            "assets_dir": payload.get("assets_dir"),
        }

        script_file = _find_script(scripts_dir)
        if not script_file:
            print(json.dumps({
                "success": False,
                "error": "No executable script found. Expected scripts/run.py or scripts/main.py",
            }, ensure_ascii=False))
            return

        module = _load_module(script_file, "dynamic_skill_runtime")
        entry = getattr(module, "run", None) or getattr(module, "main", None)
        if not callable(entry):
            print(json.dumps({
                "success": False,
                "error": "Skill script must expose a callable 'run' or 'main'",
                "script": script_file,
            }, ensure_ascii=False))
            return

        result = await _call_entrypoint(entry, arguments, context)
        print(json.dumps({"success": True, "result": _json_safe(result)}, ensure_ascii=False))


    if __name__ == "__main__":
        try:
            asyncio.run(_main())
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
            raise
    """
).strip()


@dataclass
class Skill:
    """Represents a single skill parsed from SKILL.md."""

    name: str
    description: str
    tools: List[str]
    content: str
    directory: Path


class SkillManager:
    """Manages loading, listing, and sandbox execution of skills."""

    NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    _instances: Dict[Tuple[str, str, str], "SkillManager"] = {}
    _instance_lock = threading.Lock()

    def __new__(
        cls,
        workspace_root: Optional[str] = None,
        skills_root: Optional[str] = None,
        agent_name: Optional[str] = None,
    ):
        # Normalize paths to ensure consistent singleton keys
        # Use normpath to handle different path representations (e.g., "./path" vs "path")
        workspace = os.path.normpath(
            os.path.abspath(workspace_root or os.getcwd())
        )
        skills = os.path.normpath(
            os.path.abspath(skills_root or os.path.join(workspace, "skills"))
        )
        # Ensure agent_name is always a string (None -> "")
        agent = agent_name or ""

        key = (workspace, skills, agent)

        with cls._instance_lock:
            instance = cls._instances.get(key)
            if instance is None:
                instance = super().__new__(cls)
                cls._instances[key] = instance
        return instance

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        skills_root: Optional[str] = None,
        agent_name: Optional[str] = None,
    ):
        """Initialize SkillManager (singleton per workspace/skills_root/agent_name combination).

        Args:
            workspace_root: Root directory for workspace (default: current directory)
            skills_root: Root directory for skills (default: workspace_root/skills)
            agent_name: Optional agent name for namespacing
        """
        if getattr(self, "_initialized", False):
            return

        # Normalize paths consistently with __new__
        self.workspace_root = os.path.normpath(
            os.path.abspath(workspace_root or os.getcwd())
        )
        self.skills_root = os.path.normpath(
            os.path.abspath(skills_root or os.path.join(self.workspace_root, "skills"))
        )
        self.dynamic_skills_root = os.path.join(self.skills_root, "github")
        self.agent_name = agent_name or ""

        os.makedirs(self.skills_root, exist_ok=True)
        os.makedirs(self.dynamic_skills_root, exist_ok=True)

        self._skills: Dict[str, Skill] = {}
        self._disabled_skills: Dict[str, Tuple[Skill, str]] = {}
        self._initialized = True

    @classmethod
    def get_instance(
        cls,
        workspace_root: Optional[str] = None,
        skills_root: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> "SkillManager":
        return cls(
            workspace_root=workspace_root,
            skills_root=skills_root,
            agent_name=agent_name,
        )

    @classmethod
    def reset_instances(cls):
        with cls._instance_lock:
            cls._instances.clear()

    def has_skill(self, skill_name: str) -> bool:
        return skill_name in self._skills

    def list_skill_names(self) -> List[str]:
        return sorted(self._skills.keys())

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def get_all_skills(self) -> List[Skill]:
        return [self._skills[name] for name in sorted(self._skills.keys())]

    def get_disabled_skills(self) -> Dict[str, Dict[str, Any]]:
        data: Dict[str, Dict[str, Any]] = {}
        for name, (skill, reason) in self._disabled_skills.items():
            data[name] = {
                "name": skill.name,
                "description": skill.description,
                "reason": reason,
                "path": str(skill.directory),
            }
        return data

    def list_skills(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for skill in self.get_all_skills():
            items.append(
                {
                    "name": skill.name,
                    "description": skill.description,
                    "metadata": {
                        "path": str(skill.directory),
                        "instruction": str(skill.directory / "SKILL.md"),
                        "scripts_dir": str(skill.directory / "scripts"),
                    },
                }
            )
        return items

    def get_tools(self) -> List[Dict[str, Any]]:
        """Expose loaded skills as callable function tools for LLM tool-calling.

        Returns skill tools that can be called by the agent. Each skill's parameters
        are dynamically determined from its SKILL.md content and implementation.
        For now, we use a flexible schema that accepts any parameters the skill needs.
        """
        tools: List[Dict[str, Any]] = []
        for skill in self.get_all_skills():
            # Build a flexible parameter schema that accepts any JSON object
            # The actual validation happens in the skill's run/main function
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": skill.name,
                        "description": (
                            f"{skill.description}\n\n"
                            f"Skill location: {skill.directory}\n"
                            f"This skill will be executed in a sandboxed environment with the provided parameters."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {},  # Accept any parameters
                            "required": [],
                            "additionalProperties": True,  # Allow any additional properties
                        },
                    },
                }
            )
        return tools

    async def load_skills_from_source(
        self, source: str, force_update: bool = False
    ) -> Dict[str, Any]:
        """
        Load skills from github/local source by discovering SKILL.md recursively.
        No skill code is executed in this stage.
        """
        source_path, source_meta = await asyncio.to_thread(
            self._prepare_source_path, source, force_update
        )

        loaded, errors = await asyncio.to_thread(
            self._load_skills_from_path, source_path, source_meta
        )

        if not loaded and errors:
            raise ValueError("; ".join(errors))

        return {
            "source": source,
            "resolved_path": source_path,
            "loaded_skills": sorted(loaded),
            "loaded_count": len(loaded),
            "errors": errors,
        }

    def _load_skills_from_path(
        self, source_path: str, source_meta: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        skill_files = self._discover_skill_files(source_path)
        if not skill_files:
            raise ValueError(
                "No valid skill found. A skill directory must contain SKILL.md"
            )

        loaded: List[str] = []
        errors: List[str] = []

        for skill_file in skill_files:
            try:
                skill = self._parse_skill_file(skill_file, source_meta)

                self._skills[skill.name] = skill
                loaded.append(skill.name)
            except Exception as e:
                errors.append(f"{skill_file}: {str(e)}")

        return loaded, errors

    def _prepare_source_path(
        self, source: str, force_update: bool = False
    ) -> tuple[str, Dict[str, Any]]:
        source = source.strip()
        if not source:
            raise ValueError("Skill source is required")

        if self._looks_like_github(source):
            repo_url = self._normalize_github_url(source)
            repo_slug = self._extract_repo_slug(repo_url)
            repo_name = repo_slug.split("/")[-1]
            target_dir = os.path.join(self.skills_root, repo_name)

            if not os.path.exists(target_dir):
                self._run_git_command(["clone", "--depth", "1", repo_url, target_dir])
            elif force_update:
                self._run_git_command(["-C", target_dir, "pull", "--ff-only"])

            return target_dir, {
                "type": "github",
                "repo_url": repo_url,
                "repo_slug": repo_slug,
                "repo_name": repo_name,
            }

        local_path = os.path.abspath(
            source
            if os.path.isabs(source)
            else os.path.join(self.workspace_root, source)
        )
        if not os.path.isdir(local_path):
            raise ValueError(f"Skill source path does not exist: {local_path}")
        return local_path, {"type": "local", "path": local_path}

    def _looks_like_github(self, source: str) -> bool:
        return (
            "github.com/" in source
            or source.startswith("github.com/")
            or source.startswith("git@github.com:")
        )

    def _normalize_github_url(self, source: str) -> str:
        normalized = source
        if normalized.startswith("git@github.com:"):
            normalized = normalized.replace("git@github.com:", "https://github.com/", 1)
        if normalized.startswith("github.com/"):
            normalized = f"https://{normalized}"

        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or parsed.netloc != "github.com":
            raise ValueError("Only GitHub repository URLs are supported")

        path = parsed.path.strip("/")
        parts = path.split("/")
        if len(parts) < 2:
            raise ValueError("Invalid GitHub repository URL")
        owner, repo = parts[0], parts[1]
        repo = repo.replace(".git", "")
        return f"https://github.com/{owner}/{repo}.git"

    def _extract_repo_slug(self, repo_url: str) -> str:
        match = re.search(r"github\.com/([^/]+/[^/.]+)", repo_url)
        if not match:
            raise ValueError("Unable to parse repository slug from URL")
        return match.group(1)

    def _run_git_command(self, args: List[str]) -> None:
        try:
            subprocess.run(
                ["git", *args],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError:
            raise ValueError("git is not installed on the server")
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            raise ValueError(f"Git command failed: {stderr or e}")

    def _discover_skill_files(self, source_path: str) -> List[Path]:
        result: List[Path] = []
        for root, dirs, files in os.walk(source_path):
            dirs[:] = [
                d
                for d in dirs
                if d
                not in {
                    ".git",
                    "__pycache__",
                    ".venv",
                    "venv",
                    "node_modules",
                    "dist",
                    "build",
                }
            ]
            if "SKILL.md" in files:
                result.append(Path(root) / "SKILL.md")
        return sorted(result)

    def _parse_skill_file(self, skill_file: Path, source_meta: Dict[str, Any]) -> Skill:
        content = skill_file.read_text(encoding="utf-8")
        frontmatter, markdown = self._split_frontmatter(content)
        metadata = self._parse_frontmatter_yaml(frontmatter)

        name = str(metadata.get("name", "")).strip()
        description = str(metadata.get("description", "")).strip()
        tools = metadata.get("tools", [])
        model = metadata.get("model")
        allowed_tools_field = metadata.get("allowed-tools") or metadata.get(
            "allowed_tools"
        )
        mcp = metadata.get("mcp")
        subtask = metadata.get("subtask", False)
        license_field = metadata.get("license")
        compatibility = metadata.get("compatibility")
        metadata_field = metadata.get("metadata")

        self._validate_name(name, skill_file.parent.name)
        self._validate_description(description)

        if not isinstance(tools, list):
            tools = [str(tools)] if tools else []
        tools = [str(tool).strip() for tool in tools if str(tool).strip()]

        if model is not None:
            model = str(model).strip() or None

        allowed_tools: Optional[List[str]] = None
        if allowed_tools_field is not None:
            if isinstance(allowed_tools_field, str):
                allowed_tools = [
                    item.strip() for item in allowed_tools_field.split() if item.strip()
                ]
            elif isinstance(allowed_tools_field, list):
                allowed_tools = [
                    str(item).strip()
                    for item in allowed_tools_field
                    if str(item).strip()
                ]
            else:
                raise ValueError("allowed-tools must be a string or list")

        if mcp is not None and not isinstance(mcp, dict):
            raise ValueError("mcp must be a mapping")

        if isinstance(subtask, str):
            subtask = subtask.lower() in {"true", "1", "yes"}
        else:
            subtask = bool(subtask)

        parsed_metadata: Dict[str, str] = {}
        if metadata_field is not None:
            if not isinstance(metadata_field, dict):
                raise ValueError("metadata must be a mapping")
            parsed_metadata = {str(k): str(v) for k, v in metadata_field.items()}

        if compatibility is not None:
            compatibility = str(compatibility).strip()
            if len(compatibility) > 500:
                raise ValueError("compatibility must be <= 500 characters")

        return Skill(
            name=name,
            description=description,
            tools=tools,
            content=markdown.strip(),
            directory=skill_file.parent,
        )

    def _split_frontmatter(self, content: str) -> tuple[str, str]:
        if not content.startswith("---"):
            raise ValueError("SKILL.md must start with YAML frontmatter")
        pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
        match = pattern.match(content)
        if not match:
            raise ValueError("Invalid YAML frontmatter format in SKILL.md")
        return match.group(1), match.group(2)

    def _parse_frontmatter_yaml(self, frontmatter: str) -> Dict[str, Any]:
        if yaml is not None:
            parsed = yaml.safe_load(frontmatter) or {}
        else:
            parsed = self._simple_yaml_parse(frontmatter)
        if not isinstance(parsed, dict):
            raise ValueError("Frontmatter must be a YAML mapping")
        return parsed

    def _simple_yaml_parse(self, yaml_content: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        lines = yaml_content.split("\n")
        current_key: Optional[str] = None
        current_list: Optional[List[str]] = None

        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("- ") and current_list is not None:
                current_list.append(line[2:].strip().strip('"').strip("'"))
                continue

            if ":" in line:
                if current_key and current_list is not None:
                    result[current_key] = current_list

                parts = line.split(":", 1)
                key = parts[0].strip()
                value = parts[1].strip().strip('"').strip("'")

                if value == "":
                    current_key = key
                    current_list = []
                else:
                    result[key] = value
                    current_key = None
                    current_list = None

        if current_key and current_list is not None:
            result[current_key] = current_list

        return result

    def _validate_name(self, name: str, dir_name: str):
        """Validate skill name.

        Note: We don't enforce that name must match directory name, as the skill name
        is a logical identifier while directory name is just filesystem organization.
        """
        if not name:
            raise ValueError("Missing required field: name")
        if len(name) > 64:
            raise ValueError("name must be <= 64 characters")
        if not self.NAME_PATTERN.match(name):
            raise ValueError(
                "name must contain lowercase letters/numbers and hyphens, no leading/trailing hyphen, no consecutive hyphens"
            )
        if "--" in name:
            raise ValueError("name must not contain consecutive hyphens")

    def _validate_description(self, description: str):
        if not description:
            raise ValueError("Missing required field: description")
        if len(description) > 1024:
            raise ValueError("description must be <= 1024 characters")

    async def execute_skill(self, skill_name: str, arguments: Dict[str, Any]) -> Any:
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return {
                "error": "Skill arguments must be a JSON object",
                "skill": skill_name,
            }

        skill = self._skills.get(skill_name)
        if not skill:
            return {"error": f"Skill '{skill_name}' not found", "skill": skill_name}

        return await self._execute_skill_in_sandbox(skill, arguments)

    async def _execute_skill_in_sandbox(
        self, skill: Skill, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        skill_dir = str(skill.directory)
        timeout = int(
            arguments.pop("__timeout", os.getenv("SKILL_SANDBOX_TIMEOUT", "20"))
        )
        timeout = max(3, min(timeout, 120))

        runner_code = self._build_sandbox_runner_code()
        payload = {
            "arguments": arguments,
            "skill_dir": skill_dir,
            "instruction": skill.content,
            "scripts_dir": str(skill.directory / "scripts"),
            "references_dir": str(skill.directory / "references"),
            "assets_dir": str(skill.directory / "assets"),
        }

        python_exec = os.getenv("SKILL_PYTHON_EXECUTABLE", "python3")
        env = {
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
            "PATH": os.getenv("PATH", ""),
            "LANG": os.getenv("LANG", "C.UTF-8"),
            "LC_ALL": os.getenv("LC_ALL", "C.UTF-8"),
        }

        mem_limit_mb = int(os.getenv("SKILL_SANDBOX_MEM_MB", "256"))
        file_limit_mb = int(os.getenv("SKILL_SANDBOX_FSIZE_MB", "8"))

        def _preexec_set_limits():
            if os.name != "posix":
                return
            try:
                import resource  # type: ignore
            except Exception:
                return

            try:
                cpu_soft = max(1, min(timeout, 60))
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_soft, cpu_soft + 1))
            except Exception:
                pass

            try:
                if hasattr(resource, "RLIMIT_AS"):
                    resource.setrlimit(
                        resource.RLIMIT_AS,
                        (mem_limit_mb * 1024 * 1024, mem_limit_mb * 1024 * 1024),
                    )
            except Exception:
                pass

            try:
                resource.setrlimit(
                    resource.RLIMIT_FSIZE,
                    (file_limit_mb * 1024 * 1024, file_limit_mb * 1024 * 1024),
                )
            except Exception:
                pass

        try:
            completed = await asyncio.to_thread(
                subprocess.run,
                [
                    python_exec,
                    "-I",
                    "-c",
                    runner_code,
                    json.dumps(payload, ensure_ascii=False),
                ],
                cwd=skill_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                preexec_fn=_preexec_set_limits if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Dynamic skill timed out after {timeout}s",
                "skill": skill.name,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Dynamic skill sandbox failed: {str(e)}",
                "skill": skill.name,
            }

        stdout_text = (completed.stdout or "").strip()
        stderr_text = (completed.stderr or "").strip()

        try:
            parsed: Dict[str, Any] = json.loads(stdout_text) if stdout_text else {}
        except Exception:
            parsed = {
                "success": completed.returncode == 0,
                "result": stdout_text,
                "stderr": stderr_text,
            }

        if completed.returncode != 0:
            parsed.setdefault("success", False)
            parsed.setdefault("error", "Dynamic skill process failed")
            if stderr_text:
                parsed.setdefault("stderr", stderr_text)

        parsed.setdefault("skill", skill.name)
        return parsed

    def _build_sandbox_runner_code(self) -> str:
        return SANDBOX_RUNNER_CODE
