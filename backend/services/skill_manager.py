"""
Skill Manager - Manages custom skills for agent mode
Provides extensible skill system for domain-specific capabilities
"""

import json
import inspect
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime


class Skill:
    """Base class for custom skills"""

    def __init__(self, name: str, description: str):
        """
        Initialize a skill

        Args:
            name: Skill name
            description: Skill description
        """
        self.name = name
        self.description = description

    async def execute(self, **kwargs) -> Any:
        """
        Execute the skill

        Args:
            **kwargs: Skill parameters

        Returns:
            Skill execution result
        """
        raise NotImplementedError("Skill must implement execute method")

    def get_parameters(self) -> Dict[str, Any]:
        """
        Get skill parameters schema

        Returns:
            JSON schema for skill parameters
        """
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }


class SkillManager:
    """Manager for custom skills"""

    def __init__(self):
        """Initialize Skill Manager"""
        self.skills: Dict[str, Skill] = {}
        self._register_builtin_skills()

    def register_skill(self, skill: Skill):
        """
        Register a custom skill

        Args:
            skill: Skill instance to register
        """
        self.skills[skill.name] = skill
        print(f"✓ Registered skill: {skill.name}")

    def _register_builtin_skills(self):
        """Register built-in skills"""
        # Register default skills
        self.register_skill(FileReadSkill())
        self.register_skill(FileWriteSkill())
        self.register_skill(CodeExecutionSkill())
        self.register_skill(DataAnalysisSkill())

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get all skills as OpenAI function calling tools

        Returns:
            List of tool definitions
        """
        tools = []
        for skill in self.skills.values():
            tool = {
                "type": "function",
                "function": {
                    "name": skill.name,
                    "description": skill.description,
                    "parameters": skill.get_parameters(),
                },
            }
            tools.append(tool)
        return tools

    async def execute_skill(self, skill_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a skill by name

        Args:
            skill_name: Name of the skill
            arguments: Skill arguments

        Returns:
            Skill execution result
        """
        if skill_name not in self.skills:
            raise ValueError(f"Skill '{skill_name}' not found")

        skill = self.skills[skill_name]
        try:
            result = await skill.execute(**arguments)
            return result
        except Exception as e:
            return {
                "error": f"Skill execution failed: {str(e)}",
                "skill": skill_name,
            }


# Built-in Skills

class FileReadSkill(Skill):
    """Skill for reading files"""

    def __init__(self):
        super().__init__(
            name="read_file",
            description="Read content from a file",
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read",
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8",
                },
            },
            "required": ["file_path"],
        }

    async def execute(self, file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read file content"""
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            return {
                "file_path": file_path,
                "content": content,
                "size": len(content),
            }
        except Exception as e:
            return {
                "error": str(e),
                "file_path": file_path,
            }


class FileWriteSkill(Skill):
    """Skill for writing files"""

    def __init__(self):
        super().__init__(
            name="write_file",
            description="Write content to a file",
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8",
                },
            },
            "required": ["file_path", "content"],
        }

    async def execute(
        self, file_path: str, content: str, encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Write content to file"""
        try:
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)
            return {
                "file_path": file_path,
                "bytes_written": len(content.encode(encoding)),
                "success": True,
            }
        except Exception as e:
            return {
                "error": str(e),
                "file_path": file_path,
                "success": False,
            }


class CodeExecutionSkill(Skill):
    """Skill for executing Python code (sandboxed)"""

    def __init__(self):
        super().__init__(
            name="execute_code",
            description="Execute Python code in a sandboxed environment",
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds (default: 5)",
                    "default": 5,
                },
            },
            "required": ["code"],
        }

    async def execute(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        """Execute Python code with timeout"""
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr

        try:
            # Capture stdout and stderr
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()

            # Create restricted globals (no dangerous operations)
            safe_globals = {
                "__builtins__": {
                    "print": print,
                    "len": len,
                    "range": range,
                    "str": str,
                    "int": int,
                    "float": float,
                    "list": list,
                    "dict": dict,
                    "tuple": tuple,
                    "set": set,
                    "sum": sum,
                    "max": max,
                    "min": min,
                    "abs": abs,
                    "round": round,
                },
            }

            # Execute code
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exec(code, safe_globals)

            return {
                "success": True,
                "stdout": stdout_buffer.getvalue(),
                "stderr": stderr_buffer.getvalue(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }


class DataAnalysisSkill(Skill):
    """Skill for basic data analysis"""

    def __init__(self):
        super().__init__(
            name="analyze_data",
            description="Perform basic statistical analysis on data",
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Array of numbers to analyze",
                },
                "operations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["mean", "median", "std", "min", "max", "sum"],
                    },
                    "description": "Statistical operations to perform",
                    "default": ["mean", "min", "max"],
                },
            },
            "required": ["data"],
        }

    async def execute(
        self, data: List[float], operations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Perform statistical analysis"""
        if operations is None:
            operations = ["mean", "min", "max"]

        try:
            import statistics

            results = {}

            if "mean" in operations:
                results["mean"] = statistics.mean(data)
            if "median" in operations:
                results["median"] = statistics.median(data)
            if "std" in operations:
                results["std"] = statistics.stdev(data) if len(data) > 1 else 0
            if "min" in operations:
                results["min"] = min(data)
            if "max" in operations:
                results["max"] = max(data)
            if "sum" in operations:
                results["sum"] = sum(data)

            return {
                "success": True,
                "data_points": len(data),
                "results": results,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# Example: How to create custom skills
class CustomSkillExample(Skill):
    """Example of a custom skill"""

    def __init__(self):
        super().__init__(
            name="custom_skill_example",
            description="This is an example of how to create a custom skill",
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "First parameter",
                },
                "param2": {
                    "type": "integer",
                    "description": "Second parameter",
                    "default": 10,
                },
            },
            "required": ["param1"],
        }

    async def execute(self, param1: str, param2: int = 10) -> Dict[str, Any]:
        """Execute the custom skill"""
        # Implement your custom logic here
        return {
            "result": f"Executed with {param1} and {param2}",
            "success": True,
        }
