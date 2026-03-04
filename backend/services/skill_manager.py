"""
Skill Manager - manages built-in skills and Agent Skills (SKILL.md based).

Design goals:
- Follow Agent Skills specification for SKILL.md parsing/validation.
- Borrow class structure ideas from oh-my-agent (metadata-first skill model).
- Keep two-phase model:
  1) load/download/register metadata only (no code execution)
  2) execute dynamic skills at runtime in subprocess sandbox
"""

import asyncio
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


@dataclass
class SkillDefinition:
    """Represents one discovered Agent Skill from SKILL.md."""

    name: str
    description: str
    content: str
    directory: Path
    source: str
    source_meta: Dict[str, Any] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)
    allowed_tools: Optional[List[str]] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    license: Optional[str] = None
    compatibility: Optional[str] = None


class SkillManager:
    """Manages dynamic Agent Skills discovered from SKILL.md."""

    NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        skills_root: Optional[str] = None,
    ):
        self.workspace_root = os.path.abspath(workspace_root or os.getcwd())
        self.skills_root = os.path.abspath(
            skills_root or os.path.join(self.workspace_root, "skills")
        )
        self.dynamic_skills_root = os.path.join(self.skills_root, "github")

        os.makedirs(self.skills_root, exist_ok=True)
        os.makedirs(self.dynamic_skills_root, exist_ok=True)

        self.dynamic_skills: Dict[str, SkillDefinition] = {}

    def has_skill(self, skill_name: str) -> bool:
        return skill_name in self.dynamic_skills

    def list_skill_names(self) -> List[str]:
        return sorted(self.dynamic_skills.keys())

    def list_skills(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        for name, spec in self.dynamic_skills.items():
            items.append(
                {
                    "name": name,
                    "description": spec.description,
                    "source": spec.source,
                    "metadata": {
                        "path": str(spec.directory),
                        "instruction": str(spec.directory / "SKILL.md"),
                        "scripts_dir": str(spec.directory / "scripts"),
                        "license": spec.license,
                        "compatibility": spec.compatibility,
                        "allowed_tools": spec.allowed_tools,
                        **spec.source_meta,
                        **spec.metadata,
                    },
                }
            )

        return sorted(items, key=lambda x: x["name"])

    def get_tools(self) -> List[Dict[str, Any]]:
        tools = []

        for name, spec in self.dynamic_skills.items():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": spec.description,
                        "parameters": {
                            "type": "object",
                            "description": "Dynamic skill input. Schema is defined by SKILL.md and scripts.",
                            "properties": {},
                            "required": [],
                            "additionalProperties": True,
                        },
                    },
                }
            )

        return tools

    async def load_skills_from_source(
        self, source: str, force_update: bool = False
    ) -> Dict[str, Any]:
        """
        Download/sync source and register skills by discovering SKILL.md.
        NOTE: loading stage does not execute scripts.
        """
        source_path, source_meta = await asyncio.to_thread(
            self._prepare_source_path, source, force_update
        )

        skill_files = self._discover_skill_files(source_path)
        if not skill_files:
            raise ValueError(
                "No valid skill found. A skill directory must contain SKILL.md"
            )

        loaded: List[str] = []
        errors: List[str] = []

        for skill_file in skill_files:
            try:
                parsed = self._parse_skill_file(skill_file, source_meta)
                self.dynamic_skills[parsed.name] = parsed
                loaded.append(parsed.name)
            except Exception as e:
                errors.append(f"{skill_file}: {str(e)}")

        if not loaded and errors:
            raise ValueError("; ".join(errors))

        return {
            "source": source,
            "resolved_path": source_path,
            "loaded_skills": sorted(loaded),
            "loaded_count": len(loaded),
            "errors": errors,
        }

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
            source if os.path.isabs(source) else os.path.join(self.workspace_root, source)
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

    def _parse_skill_file(self, skill_file: Path, source_meta: Dict[str, Any]) -> SkillDefinition:
        content = skill_file.read_text(encoding="utf-8")
        frontmatter, body = self._split_frontmatter(content)
        metadata = self._parse_frontmatter_yaml(frontmatter)

        name = str(metadata.get("name", "")).strip()
        description = str(metadata.get("description", "")).strip()
        license_field = metadata.get("license")
        compatibility = metadata.get("compatibility")
        metadata_field = metadata.get("metadata")
        allowed_tools_field = metadata.get("allowed-tools")

        self._validate_name(name, skill_file.parent.name)
        self._validate_description(description)

        if compatibility is not None:
            compatibility = str(compatibility).strip()
            if len(compatibility) > 500:
                raise ValueError("compatibility must be <= 500 characters")

        parsed_metadata: Dict[str, str] = {}
        if metadata_field is not None:
            if not isinstance(metadata_field, dict):
                raise ValueError("metadata must be a mapping")
            parsed_metadata = {str(k): str(v) for k, v in metadata_field.items()}

        allowed_tools: Optional[List[str]] = None
        if allowed_tools_field is not None:
            if isinstance(allowed_tools_field, str):
                allowed_tools = [item for item in allowed_tools_field.split() if item.strip()]
            elif isinstance(allowed_tools_field, list):
                allowed_tools = [str(item).strip() for item in allowed_tools_field if str(item).strip()]
            else:
                raise ValueError("allowed-tools must be a string or list")

        return SkillDefinition(
            name=name,
            description=description,
            content=body.strip(),
            directory=skill_file.parent,
            source=source_meta.get("type", "dynamic"),
            source_meta=source_meta,
            tools=[],
            allowed_tools=allowed_tools,
            metadata=parsed_metadata,
            license=str(license_field).strip() if license_field else None,
            compatibility=compatibility,
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
        if name != dir_name:
            raise ValueError(
                f"name '{name}' must match parent directory name '{dir_name}'"
            )

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

        spec = self.dynamic_skills.get(skill_name)
        if not spec:
            return {"error": f"Skill '{skill_name}' not found", "skill": skill_name}

        return await self._execute_dynamic_skill_in_sandbox(spec, arguments)

    async def _execute_dynamic_skill_in_sandbox(
        self, spec: SkillDefinition, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        skill_dir = str(spec.directory)
        timeout = int(arguments.pop("__timeout", os.getenv("SKILL_SANDBOX_TIMEOUT", "20")))
        timeout = max(3, min(timeout, 120))

        runner_code = self._build_sandbox_runner_code()
        payload = {
            "arguments": arguments,
            "skill_dir": skill_dir,
            "instruction": spec.content,
            "scripts_dir": str(spec.directory / "scripts"),
            "references_dir": str(spec.directory / "references"),
            "assets_dir": str(spec.directory / "assets"),
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
                [python_exec, "-I", "-c", runner_code, json.dumps(payload, ensure_ascii=False)],
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
                "skill": spec.name,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Dynamic skill sandbox failed: {str(e)}",
                "skill": spec.name,
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

        parsed.setdefault("skill", spec.name)
        return parsed

    def _build_sandbox_runner_code(self) -> str:
        return r'''
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
'''
