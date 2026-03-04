"""
Permission Service - Fine-grained access control for code operations
Implements allow/deny/ask rules with wildcard pattern matching
"""

import fnmatch
import os
from typing import Dict, Literal

ActionType = Literal["allow", "deny", "ask"]


class PermissionService:
    """Permission checking service for code operations"""

    def __init__(self, rules: Dict[str, Dict[str, str]] | None = None):
        """
        Initialize with permission rules

        Args:
            rules: Permission rules in format:
                {
                    "tool_name": {
                        "pattern": "action",  # action: allow, deny, ask
                        ...
                    },
                    ...
                }

        Example:
            {
                "read": {"*": "allow", "*.env": "ask"},
                "edit": {"*": "allow", "/etc/*": "deny"},
                "bash": {"*": "ask", "ls *": "allow", "rm *": "deny"}
            }
        """
        self.rules = rules or self._default_rules()

    def _default_rules(self) -> Dict[str, Dict[str, str]]:
        """
        Default permission rules (security-first approach)

        Returns:
            dict: Default permission configuration
        """
        return {
            "read": {
                "*": "allow",  # Allow reading all files by default
                "*.env": "ask",  # Ask before reading .env files
                ".env": "ask",
                "*.key": "ask",  # Ask before reading key files
                "*.pem": "ask",  # Ask before reading PEM files
            },
            "write": {
                "*": "allow",  # Allow writing files by default
                "/etc/*": "deny",  # Deny writing to /etc
                "/usr/*": "deny",  # Deny writing to /usr
                "/bin/*": "deny",  # Deny writing to /bin
            },
            "edit": {
                "*": "allow",  # Allow editing by default
                "/etc/*": "deny",  # Deny editing system files
                "/usr/*": "deny",
                "/bin/*": "deny",
            },
            "glob": {
                "*": "allow",  # Allow file listing
            },
            "grep": {
                "*": "allow",  # Allow content search
            },
            "bash": {
                "*": "ask",  # Always ask for bash commands by default
                "ls *": "allow",  # Safe read-only commands
                "cat *": "allow",
                "pwd": "allow",
                "echo *": "allow",
                "which *": "allow",
                "rm *": "deny",  # Dangerous commands denied
                "sudo *": "deny",
                "dd *": "deny",
                "mkfs*": "deny",
                "format*": "deny",
            },
        }

    def check(
        self, tool: str, target: str, workspace_root: str | None = None
    ) -> ActionType:
        """
        Check if operation is allowed

        Args:
            tool: Tool name (read, write, edit, bash, etc.)
            target: Target resource (file path, command, etc.)
            workspace_root: Workspace root for path normalization

        Returns:
            ActionType: "allow", "deny", or "ask"
        """
        if tool not in self.rules:
            # Unknown tool - default to ask for safety
            return "ask"

        tool_rules = self.rules[tool]

        # Normalize target path if workspace_root is provided
        # BUT: don't normalize bash commands (they're not paths)
        normalized_target = target
        if workspace_root and not target.startswith("/") and tool != "bash":
            # Make relative paths absolute for pattern matching
            normalized_target = os.path.normpath(
                os.path.join(workspace_root, target)
            )

        # Match against patterns in order
        # More specific patterns should be checked first
        matched_action = None

        for pattern, action in sorted(
            tool_rules.items(), key=lambda x: -len(x[0])  # Longer patterns first
        ):
            if self._match_pattern(normalized_target, pattern):
                matched_action = action
                break

        # Default to deny if no match (security-first)
        return matched_action or "deny"

    def _match_pattern(self, target: str, pattern: str) -> bool:
        """
        Match target against wildcard pattern

        Supports:
        - * wildcard (any characters)
        - ? wildcard (single character)
        - Exact matches

        Args:
            target: Target string to match
            pattern: Pattern with wildcards

        Returns:
            bool: True if matches, False otherwise
        """
        # Exact match
        if target == pattern:
            return True

        # Wildcard match
        if fnmatch.fnmatch(target, pattern):
            return True

        # For bash commands, also check if target starts with pattern
        # e.g., "ls -la" should match "ls *"
        if " " in target:
            command = target.split()[0]
            if fnmatch.fnmatch(command, pattern.split()[0]):
                return True

        return False

    def update_rules(self, tool: str, pattern: str, action: ActionType):
        """
        Update a specific permission rule

        Args:
            tool: Tool name
            pattern: Pattern to match
            action: Action to take (allow/deny/ask)
        """
        if tool not in self.rules:
            self.rules[tool] = {}

        self.rules[tool][pattern] = action

    def remove_rule(self, tool: str, pattern: str):
        """
        Remove a specific permission rule

        Args:
            tool: Tool name
            pattern: Pattern to remove
        """
        if tool in self.rules and pattern in self.rules[tool]:
            del self.rules[tool][pattern]

    def get_rules(self) -> Dict[str, Dict[str, str]]:
        """
        Get all current permission rules

        Returns:
            dict: Current permission configuration
        """
        return self.rules.copy()

    def reset_to_defaults(self):
        """Reset all rules to default configuration"""
        self.rules = self._default_rules()


# Convenience function for testing
def test_permissions():
    """Test permission service with various scenarios"""
    perm = PermissionService()

    test_cases = [
        ("read", "README.md", "allow"),
        ("read", ".env", "ask"),
        ("read", "config.key", "ask"),
        ("edit", "/etc/hosts", "deny"),
        ("edit", "main.py", "allow"),
        ("bash", "ls -la", "allow"),
        ("bash", "rm -rf /", "deny"),
        ("bash", "python test.py", "ask"),
        ("write", "/usr/bin/test", "deny"),
        ("write", "output.txt", "allow"),
    ]

    print("Permission Service Test Results:")
    print("=" * 60)

    for tool, target, expected in test_cases:
        result = perm.check(tool, target)
        status = "✓" if result == expected else "✗"
        print(f"{status} {tool:8s} {target:30s} -> {result:8s} (expected: {expected})")

    print("=" * 60)


if __name__ == "__main__":
    test_permissions()
