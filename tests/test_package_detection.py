"""Tests for package info detection functions in build.py"""

import unittest
from unittest.mock import patch
import tempfile
import os

from mcp_server_automation.build import BuildCommand


class TestPackageInfoDetection(unittest.TestCase):
    """Test package manager and dependency detection functions."""

    def setUp(self):
        self.build_cmd = BuildCommand()

    def test_detect_package_info_with_command_override(self):
        """Test package info detection with command override."""
        with tempfile.TemporaryDirectory() as temp_dir:
            command_override = ["python", "-m", "custom_server", "--port", "8080"]
            env_vars = {"DEBUG": "true", "PORT": "8080"}

            result = self.build_cmd._detect_package_info(
                temp_dir, command_override, env_vars
            )

            self.assertEqual(result["start_command"], command_override)
            self.assertEqual(result["environment_variables"], env_vars)
            self.assertEqual(result["manager"], "pip")
            expected_entrypoint = [
                "mcp-proxy",
                "--debug",
                "--port",
                "8000",
                "--shell",
                "python",
                "--",
                "-m",
                "custom_server",
                "--port",
                "8080",
            ]
            self.assertEqual(result["entrypoint_command"], expected_entrypoint)

    def test_detect_package_info_pyproject_toml_uv(self):
        """Test detection of uv package manager from pyproject.toml."""
        pyproject_content = """
[tool.uv]
dev-dependencies = ["pytest>=6.0"]

[project]
name = "my-mcp-server"
version = "0.1.0"
dependencies = ["requests"]

[project.scripts]
my-server = "my_server:main"
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            pyproject_path = os.path.join(temp_dir, "pyproject.toml")
            with open(pyproject_path, "w") as f:
                f.write(pyproject_content)

            result = self.build_cmd._detect_package_info(temp_dir)

            self.assertEqual(result["manager"], "uv")
            self.assertEqual(result["project_file"], "pyproject.toml")
            self.assertEqual(result["start_command"], ["my-server"])

    def test_detect_package_info_pyproject_toml_poetry(self):
        """Test detection of poetry package manager from pyproject.toml."""
        pyproject_content = """
[tool.poetry]
name = "my-server"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.8"
requests = "^2.25.0"

[project.scripts]
poetry-server = "my_server:main"
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            pyproject_path = os.path.join(temp_dir, "pyproject.toml")
            with open(pyproject_path, "w") as f:
                f.write(pyproject_content)

            with patch(
                "mcp_server_automation.build.BuildCommand._extract_start_command_from_readme",
                return_value=(None, False, False),  # Returns tuple: (command, has_docker_commands, has_any_commands)
            ):
                result = self.build_cmd._detect_package_info(temp_dir)

            self.assertEqual(result["manager"], "poetry")
            self.assertEqual(result["project_file"], "pyproject.toml")
            self.assertEqual(result["start_command"], ["poetry-server"])

    def test_detect_package_info_requirements_txt(self):
        """Test detection of requirements.txt."""
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_path = os.path.join(temp_dir, "requirements.txt")
            with open(requirements_path, "w") as f:
                f.write("requests>=2.25.0\nclick>=8.0.0\n")

            # Need to provide a command since requirements.txt alone doesn't provide start command
            with patch(
                "mcp_server_automation.build.BuildCommand._extract_start_command_from_readme",
                return_value=(["python", "-m", "my_server"], False, True),
            ):
                result = self.build_cmd._detect_package_info(temp_dir)

            self.assertEqual(result["manager"], "pip")
            self.assertEqual(result["requirements_file"], "requirements.txt")
            self.assertEqual(result["start_command"], ["python", "-m", "my_server"])

    def test_detect_package_info_setup_py(self):
        """Test detection of setup.py."""
        setup_content = """
from setuptools import setup

setup(
    name="my-server",
    version="0.1.0",
    entry_points={
        'console_scripts': [
            'setup-server=my_server.main:main',
            'other-script=my_server.other:run',
        ],
    },
)
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            setup_path = os.path.join(temp_dir, "setup.py")
            with open(setup_path, "w") as f:
                f.write(setup_content)

            with patch(
                "mcp_server_automation.build.BuildCommand._extract_start_command_from_readme",
                return_value=(None, False, False),  # Returns tuple: (command, has_docker_commands, has_any_commands)
            ):
                with patch(
                    "mcp_server_automation.build.BuildCommand._extract_start_command_from_setup_py",
                    return_value=["setup-server"],
                ):
                    result = self.build_cmd._detect_package_info(temp_dir)

            self.assertEqual(result["manager"], "pip")
            self.assertEqual(result["project_file"], "setup.py")
            self.assertEqual(result["start_command"], ["setup-server"])

    # NOTE: _detect_fallback_start_command method doesn't exist in current BuildCommand
    # These tests have been removed as they test non-existent functionality

    def test_extract_start_command_from_pyproject_no_scripts(self):
        """Test pyproject.toml parsing when no console scripts exist."""
        pyproject_content = """
[project]
name = "my-server"
version = "0.1.0"
dependencies = ["requests"]
"""

        result = self.build_cmd._extract_start_command_from_pyproject(pyproject_content)
        self.assertIsNone(result)

    def test_extract_start_command_from_pyproject_entry_points(self):
        """Test pyproject.toml parsing with entry-points format."""
        pyproject_content = """
[project]
name = "my-server"
version = "0.1.0"

[project.entry-points.console_scripts]
entry-server = "my_server:main"
"""

        result = self.build_cmd._extract_start_command_from_pyproject(pyproject_content)
        self.assertEqual(result, ["entry-server"])

    def test_extract_start_command_from_setup_py_no_scripts(self):
        """Test setup.py parsing when no console scripts exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_content = """
from setuptools import setup

setup(
    name="my-server",
    version="0.1.0",
    packages=["my_server"],
)
"""
            setup_path = os.path.join(temp_dir, "setup.py")
            with open(setup_path, "w") as f:
                f.write(setup_content)

            result = self.build_cmd._extract_start_command_from_setup_py(temp_dir)
            self.assertIsNone(result)

    def test_aws_documentation_mcp_server_detection(self):
        """Test package detection for AWS Documentation MCP Server structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create AWS documentation MCP server structure
            pyproject_content = """
[project]
name = "mcp-server-aws-documentation"
version = "0.1.0"
description = "MCP server for AWS documentation"
dependencies = [
    "requests>=2.25.0",
    "beautifulsoup4>=4.9.0",
    "mcp>=1.0.0"
]

[project.scripts]
mcp-server-aws-documentation = "aws_documentation_mcp_server:main"

[tool.uv]
dev-dependencies = [
    "pytest>=6.0",
    "black",
    "ruff"
]
"""
            # Create README with MCP server configuration
            readme_content = """
# AWS Documentation MCP Server

## Usage

```json
{
  "mcpServers": {
    "aws-documentation": {
      "command": "uvx",
      "args": ["mcp-server-aws-documentation"]
    }
  }
}
```

## Development

Install with uv:
```bash
uv run mcp-server-aws-documentation
```
"""
            
            pyproject_path = os.path.join(temp_dir, "pyproject.toml")
            readme_path = os.path.join(temp_dir, "README.md")
            
            with open(pyproject_path, "w") as f:
                f.write(pyproject_content)
            with open(readme_path, "w") as f:
                f.write(readme_content)

            result = self.build_cmd._detect_package_info(temp_dir)

            # Should detect uv as package manager
            self.assertEqual(result["manager"], "uv")
            self.assertEqual(result["project_file"], "pyproject.toml")
            
            # Should extract command from README (uvx mcp-server-aws-documentation)
            expected_command = ["uvx", "mcp-server-aws-documentation"]
            self.assertEqual(result["start_command"], expected_command)
            
            # Should generate proper entrypoint command
            expected_entrypoint = [
                "mcp-proxy", "--debug", "--port", "8000", "--shell",
                "uvx", "--", "mcp-server-aws-documentation"
            ]
            self.assertEqual(result["entrypoint_command"], expected_entrypoint)

    def test_python_uv_project_fallback_to_script(self):
        """Test that uv projects fall back to pyproject.toml scripts when README doesn't have commands."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pyproject_content = """
[project]
name = "python-mcp-server"
version = "0.1.0"
dependencies = ["mcp>=1.0.0"]

[project.scripts]
python-mcp-server = "python_mcp_server.main:main"

[tool.uv]
dev-dependencies = ["pytest"]
"""
            readme_content = """
# Python MCP Server

A simple MCP server implementation.

## Installation

```bash
uv sync
```
"""
            
            pyproject_path = os.path.join(temp_dir, "pyproject.toml")
            readme_path = os.path.join(temp_dir, "README.md")
            
            with open(pyproject_path, "w") as f:
                f.write(pyproject_content)
            with open(readme_path, "w") as f:
                f.write(readme_content)

            result = self.build_cmd._detect_package_info(temp_dir)

            # Should detect uv as package manager
            self.assertEqual(result["manager"], "uv")
            self.assertEqual(result["project_file"], "pyproject.toml")
            
            # Should fall back to pyproject.toml script since no command in README
            expected_command = ["python-mcp-server"]
            self.assertEqual(result["start_command"], expected_command)

    def test_python_pip_with_requirements_txt(self):
        """Test Python project with requirements.txt (pip-based)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_content = """
mcp>=1.0.0
requests>=2.25.0
click>=8.0.0
"""
            readme_content = """
# Simple MCP Server

## Configuration

```json
{
  "mcpServers": {
    "simple": {
      "command": "python",
      "args": ["-m", "simple_mcp_server"]
    }
  }
}
```
"""
            
            requirements_path = os.path.join(temp_dir, "requirements.txt")
            readme_path = os.path.join(temp_dir, "README.md")
            
            with open(requirements_path, "w") as f:
                f.write(requirements_content)
            with open(readme_path, "w") as f:
                f.write(readme_content)

            result = self.build_cmd._detect_package_info(temp_dir)

            # Should detect pip as package manager
            self.assertEqual(result["manager"], "pip")
            self.assertEqual(result["requirements_file"], "requirements.txt")
            
            # Should extract command from README
            expected_command = ["python", "-m", "simple_mcp_server"]
            self.assertEqual(result["start_command"], expected_command)


if __name__ == "__main__":
    unittest.main()
