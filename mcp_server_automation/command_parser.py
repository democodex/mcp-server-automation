"""Command parsing utilities for MCP server automation."""

import json
import os
import re
import toml
from typing import Optional, List, Tuple


class CommandParser:
    """Handles parsing commands from various sources (README, pyproject.toml, setup.py)."""

    def extract_from_readme(
        self, mcp_server_path: str
    ) -> Tuple[Optional[List[str]], bool, bool]:
        """Extract start command from README files containing MCP server JSON config.

        Returns:
            tuple: (command, has_docker_commands, has_any_commands)
        """
        readme_files = [
            "README.md",
            "README.txt",
            "README.rst",
            "readme.md",
            "readme.txt",
        ]

        has_docker_commands = False
        has_any_commands = False

        for readme_file in readme_files:
            readme_path = os.path.join(mcp_server_path, readme_file)
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Find individual JSON blocks first, then check their content
                    json_blocks = re.findall(r'```json\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE)

                    for json_str in json_blocks:
                        # Check if this block contains MCP server configuration
                        if 'mcpServers' not in json_str and ('mcp' not in json_str or 'servers' not in json_str):
                            continue

                        try:
                            config = json.loads(json_str)

                            # Handle both formats: "mcpServers" and "mcp.servers"
                            servers = {}
                            if "mcpServers" in config:
                                servers = config["mcpServers"]
                            elif "mcp" in config and "servers" in config["mcp"]:
                                servers = config["mcp"]["servers"]

                            # Check all server commands to detect what's available
                            for server_config in servers.values():
                                if "command" in server_config:
                                    has_any_commands = True
                                    command = [server_config["command"]]
                                    if (
                                        "args" in server_config
                                        and server_config["args"]
                                    ):
                                        command.extend(server_config["args"])

                                    # Track if we found Docker commands
                                    if command[0] == "docker":
                                        has_docker_commands = True
                                    else:
                                        # Return first non-Docker command found
                                        print(
                                            f"Found MCP server command: {' '.join(command)}"
                                        )
                                        return command, has_docker_commands, has_any_commands
                        except json.JSONDecodeError:
                            continue

                except (IOError, UnicodeDecodeError):
                    continue

        return None, has_docker_commands, has_any_commands

    def extract_from_pyproject(self, content: str) -> Optional[List[str]]:
        """Extract start command from pyproject.toml."""
        try:
            # Parse TOML content
            parsed = toml.loads(content)

            # Check for console scripts
            if "project" in parsed and "scripts" in parsed["project"]:
                # Take the first script entry
                script_name = list(parsed["project"]["scripts"].keys())[0]
                return [script_name]

            # Check for entry points
            if "project" in parsed and "entry-points" in parsed["project"]:
                console_scripts = parsed["project"]["entry-points"].get(
                    "console_scripts", {}
                )
                if console_scripts:
                    script_name = list(console_scripts.keys())[0]
                    return [script_name]

            return None
        except Exception:
            return None

    def extract_from_setup_py(self, mcp_server_path: str) -> Optional[List[str]]:
        """Extract start command from setup.py."""
        setup_py_path = os.path.join(mcp_server_path, "setup.py")
        try:
            with open(setup_py_path, "r", encoding='utf-8') as f:
                content = f.read()

            # Look for entry_points console_scripts
            console_scripts_match = re.search(
                r"console_scripts.*?=.*?\[(.*?)\]", content, re.DOTALL
            )
            if console_scripts_match:
                scripts_content = console_scripts_match.group(1)
                # Extract first script name
                script_match = re.search(r'["\']([^"\'=]+)\s*=', scripts_content)
                if script_match:
                    return [script_match.group(1)]

            return None
        except Exception:
            return None