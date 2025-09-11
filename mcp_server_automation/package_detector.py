"""Package detection utilities for MCP server automation."""

import os
import toml
from typing import Optional, List, Dict, Any
import os.path

from .command_parser import CommandParser


class PackageDetector:
    """Handles detection of package managers, languages, and build configurations."""

    def __init__(self):
        self.command_parser = CommandParser()

    def detect_language_from_command(self, command: str) -> str:
        """Detect language from entrypoint command."""
        if command in ["npx", "npm", "node", "yarn", "pnpm"]:
            return "nodejs"
        elif command in ["python", "python3", "pip", "uvx", "uv"]:
            return "python"
        elif command.startswith("@"):
            # NPM package (e.g., @modelcontextprotocol/server-everything)
            return "nodejs"
        else:
            # Default to python for unknown commands
            return "python"

    def detect_language(self, mcp_server_path: str) -> str:
        """Detect the primary language/runtime of the MCP server."""
        # Validate path first
        safe_path = self._validate_path(mcp_server_path)
        
        # Check for Node.js indicators
        if os.path.exists(os.path.join(safe_path, "package.json")):
            return "nodejs"

        # Check for TypeScript indicators
        if (os.path.exists(os.path.join(mcp_server_path, "tsconfig.json")) or
            any(f.endswith('.ts') for f in os.listdir(mcp_server_path) if os.path.isfile(os.path.join(mcp_server_path, f)))):
            return "nodejs"

        # Check for Python indicators
        if (os.path.exists(os.path.join(mcp_server_path, "requirements.txt")) or
            os.path.exists(os.path.join(mcp_server_path, "pyproject.toml")) or
            os.path.exists(os.path.join(mcp_server_path, "setup.py")) or
            any(f.endswith('.py') for f in os.listdir(mcp_server_path) if os.path.isfile(os.path.join(mcp_server_path, f)))):
            return "python"

        # Default to Python if unclear
        return "python"

    def detect_package_info(
        self,
        mcp_server_path: str,
        command_override: Optional[List[str]] = None,
        environment_variables: Optional[dict] = None,
        github_url: Optional[str] = None,
        subfolder: Optional[str] = None,
        branch: Optional[str] = None,
        entrypoint_command: Optional[str] = None,
        entrypoint_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Detect package manager, dependency files, and start command."""
        # Check if this is entrypoint mode
        is_entrypoint_mode = entrypoint_command is not None

        if is_entrypoint_mode:
            # For entrypoint mode, detect language from command
            language = self.detect_language_from_command(entrypoint_command)
        else:
            # First detect the language/runtime from filesystem
            language = self.detect_language(mcp_server_path)

        package_info = {
            "language": language,
            "manager": "pip" if language == "python" else "npm",
            "requirements_file": None,
            "project_file": None,
            "start_command": None,
            "environment_variables": environment_variables or {},
            "github_url": github_url,
            "subfolder": subfolder,
            "branch": branch or "main",
            "is_entrypoint_mode": is_entrypoint_mode,
            "entrypoint_command": entrypoint_command,
            "entrypoint_args": entrypoint_args or [],
        }

        # Priority 1: Use entrypoint command if provided
        if is_entrypoint_mode:
            # Convert entrypoint command and args to start_command format
            full_command = [entrypoint_command]
            if entrypoint_args:
                full_command.extend(entrypoint_args)
            package_info["start_command"] = full_command
            print(f"Using entrypoint command: {' '.join(full_command)}")
        # Priority 2: Use command override if provided
        elif command_override:
            package_info["start_command"] = command_override
            print(f"Using command override: {' '.join(command_override)}")
        else:
            # Priority 2: Try to extract from README files first (most reliable)
            readme_command, has_docker_commands, has_any_commands = self.command_parser.extract_from_readme(
                mcp_server_path
            )
            package_info["start_command"] = readme_command

            # Validate bootstrap command requirements
            if not readme_command:
                if has_docker_commands:
                    # Only Docker commands found, no suitable non-Docker commands
                    raise ValueError(
                        "README contains only Docker commands for MCP server configuration. "
                        "Please provide a command_override in your configuration to specify "
                        "how to run the MCP server directly (without Docker). "
                        "Example:\n"
                        "build:\n"
                        "  command_override:\n"
                        "    - \"python\"\n"
                        "    - \"-m\"\n"
                        "    - \"your_server_module\""
                    )
                elif has_any_commands:
                    # Commands found but couldn't parse them properly
                    raise ValueError(
                        "Could not parse MCP server commands from README. "
                        "Please provide a command_override in your configuration. "
                        "Example:\n"
                        "build:\n"
                        "  command_override:\n"
                        "    - \"python\"\n"
                        "    - \"server.py\""
                    )

        # Check for different dependency files and extract start command based on language
        if language == "nodejs":
            # Handle Node.js dependencies
            if os.path.exists(os.path.join(mcp_server_path, "package.json")):
                package_info["project_file"] = "package.json"
                package_info["manager"] = "npm"
                # Note: For Node.js, we rely on README commands only, not package.json parsing
        else:
            # Handle Python dependencies
            if os.path.exists(os.path.join(mcp_server_path, "pyproject.toml")):
                with open(os.path.join(mcp_server_path, "pyproject.toml"), "r", encoding='utf-8') as f:
                    content = f.read()
                    if "[tool.uv]" in content:
                        package_info["manager"] = "uv"
                    elif "[tool.poetry]" in content:
                        package_info["manager"] = "poetry"
                    package_info["project_file"] = "pyproject.toml"

                    # Try to extract console_scripts or main module (only if not found in README)
                    if not package_info["start_command"]:
                        package_info["start_command"] = (
                            self.command_parser.extract_from_pyproject(content)
                        )

            elif os.path.exists(os.path.join(mcp_server_path, "requirements.txt")):
                package_info["requirements_file"] = "requirements.txt"

            elif os.path.exists(os.path.join(mcp_server_path, "setup.py")):
                package_info["project_file"] = "setup.py"
                if not package_info["start_command"]:
                    package_info["start_command"] = (
                        self.command_parser.extract_from_setup_py(mcp_server_path)
                    )

        # Final validation: ensure we have a command if no command_override was provided
        if not package_info["start_command"] and not command_override:
            raise ValueError(
                "Could not detect MCP server startup command from README or project files. "
                "Please provide a command_override in your configuration to specify "
                "how to run the MCP server. "
                "Example:\n"
                "build:\n"
                "  command_override:\n"
                "    - \"python\"\n"
                "    - \"-m\"\n"
                "    - \"your_server_module\""
            )

        return package_info
    
    def _validate_path(self, path: str) -> str:
        """Validate file path to prevent traversal attacks."""
        abs_path = os.path.abspath(path)
        if '..' in path or abs_path != os.path.normpath(abs_path):
            raise ValueError(f"Invalid path detected: {path}")
        return abs_path