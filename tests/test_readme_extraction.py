"""Tests for README command extraction functionality in build.py"""

import unittest
import tempfile
import os

from mcp_server_automation.build import BuildCommand


class TestReadmeCommandExtraction(unittest.TestCase):
    """Test README command extraction functions."""

    def setUp(self):
        self.build_cmd = BuildCommand()

    def test_extract_command_from_claude_desktop_format(self):
        """Test extraction from Claude Desktop mcpServers format."""
        readme_content = '''# MCP Server

This is a test MCP server.

## Usage with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "everything": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-everything"
      ]
    }
  }
}
```

## Other Information

Some other content here.
'''

        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write(readme_content)

            command, has_docker, has_any = self.build_cmd._extract_start_command_from_readme(temp_dir)

            self.assertEqual(command, ["npx", "-y", "@modelcontextprotocol/server-everything"])
            self.assertFalse(has_docker)
            self.assertTrue(has_any)

    def test_extract_command_from_vscode_format(self):
        """Test extraction from VS Code mcp.servers format."""
        readme_content = '''# MCP Server

## Usage with VS Code

```json
{
  "mcp": {
    "servers": {
      "everything": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-everything"]
      }
    }
  }
}
```
'''

        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write(readme_content)

            command, has_docker, has_any = self.build_cmd._extract_start_command_from_readme(temp_dir)

            self.assertEqual(command, ["npx", "-y", "@modelcontextprotocol/server-everything"])
            self.assertFalse(has_docker)
            self.assertTrue(has_any)

    def test_extract_command_skips_docker_commands(self):
        """Test that Docker commands are detected but not returned."""
        readme_content = '''# MCP Server

## Usage with Docker

```json
{
  "mcpServers": {
    "docker-server": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp/server"]
    }
  }
}
```

## Usage with NPX

```json
{
  "mcpServers": {
    "npx-server": {
      "command": "python",
      "args": ["-m", "server"]
    }
  }
}
```
'''

        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write(readme_content)

            command, has_docker, has_any = self.build_cmd._extract_start_command_from_readme(temp_dir)

            self.assertEqual(command, ["python", "-m", "server"])
            self.assertTrue(has_docker)
            self.assertTrue(has_any)

    def test_extract_command_multiple_json_blocks(self):
        """Test extraction when there are multiple JSON blocks with different content."""
        readme_content = '''# MCP Server

## Example annotation

```json
{
  "priority": 1.0,
  "audience": ["user", "assistant"]
}
```

## Logging format

```json
{
  "method": "notifications/message",
  "params": {
    "level": "info",
    "data": "Info-level message"
  }
}
```

## Usage with Claude Desktop

```json
{
  "mcpServers": {
    "everything": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-everything"
      ]
    }
  }
}
```
'''

        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write(readme_content)

            command, has_docker, has_any = self.build_cmd._extract_start_command_from_readme(temp_dir)

            self.assertEqual(command, ["npx", "-y", "@modelcontextprotocol/server-everything"])
            self.assertFalse(has_docker)
            self.assertTrue(has_any)

    def test_extract_command_no_mcp_config(self):
        """Test when README has JSON blocks but no MCP server config."""
        readme_content = '''# MCP Server

## Configuration

```json
{
  "settings": {
    "debug": true,
    "port": 8080
  }
}
```

## Package info

```json
{
  "name": "my-server",
  "version": "1.0.0"
}
```
'''

        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write(readme_content)

            command, has_docker, has_any = self.build_cmd._extract_start_command_from_readme(temp_dir)

            self.assertIsNone(command)
            self.assertFalse(has_docker)
            self.assertFalse(has_any)

    def test_extract_command_invalid_json(self):
        """Test handling of invalid JSON in README."""
        readme_content = '''# MCP Server

## Usage

```json
{
  "mcpServers": {
    "server": {
      "command": "npx"
      "args": ["missing-comma"]
    }
  }
}
```

## Valid config

```json
{
  "mcpServers": {
    "valid-server": {
      "command": "python",
      "args": ["-m", "server"]
    }
  }
}
```
'''

        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write(readme_content)

            command, has_docker, has_any = self.build_cmd._extract_start_command_from_readme(temp_dir)

            # Should skip the invalid JSON and use the valid one
            self.assertEqual(command, ["python", "-m", "server"])
            self.assertFalse(has_docker)
            self.assertTrue(has_any)

    def test_extract_command_no_readme(self):
        """Test when no README file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            command, has_docker, has_any = self.build_cmd._extract_start_command_from_readme(temp_dir)

            self.assertIsNone(command)
            self.assertFalse(has_docker)
            self.assertFalse(has_any)

    def test_extract_command_mixed_formats(self):
        """Test when README contains both Claude Desktop and VS Code formats."""
        readme_content = '''# MCP Server

## Usage with Claude Desktop

```json
{
  "mcpServers": {
    "claude-server": {
      "command": "python",
      "args": ["-m", "claude_server"]
    }
  }
}
```

## Usage with VS Code

```json
{
  "mcp": {
    "servers": {
      "vscode-server": {
        "command": "node",
        "args": ["vscode_server.js"]
      }
    }
  }
}
```
'''

        with tempfile.TemporaryDirectory() as temp_dir:
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write(readme_content)

            command, has_docker, has_any = self.build_cmd._extract_start_command_from_readme(temp_dir)

            # Should return the first non-Docker command found
            self.assertEqual(command, ["python", "-m", "claude_server"])
            self.assertFalse(has_docker)
            self.assertTrue(has_any)


if __name__ == "__main__":
    unittest.main()