"""Common utilities for MCP server automation."""

import hashlib
import re
from datetime import datetime
from typing import Optional


class Utils:
    """Common utility functions."""

    @staticmethod
    def clean_package_name(package_name: str) -> str:
        """Clean package name for Docker image naming."""
        return package_name.replace('@', '').replace('/', '-').lower()

    @staticmethod
    def extract_package_name_from_args(args: list) -> Optional[str]:
        """Extract package name from command arguments."""
        if not args:
            return None
            
        # Look for package names (typically the last argument or after flags)
        for arg in reversed(args):
            if not arg.startswith('-') and ('/' in arg or '@' in arg or not arg.startswith('-')):
                # Extract package name from patterns like:
                # @modelcontextprotocol/server-everything -> server-everything
                # mcp-server-automation -> mcp-server-automation  
                if '/' in arg:
                    return arg.split('/')[-1]
                elif '@' in arg and not arg.startswith('@'):
                    return arg.split('@')[0]
                else:
                    return arg
        return None

    @staticmethod
    def generate_static_tag() -> str:
        """Generate a static tag for entrypoint mode."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"static-{timestamp}"

    @staticmethod
    def generate_dynamic_tag(github_url: str, branch: Optional[str] = None) -> str:
        """Generate a dynamic tag based on GitHub URL and branch."""
        # Create a hash of the GitHub URL + branch for uniqueness
        content = f"{github_url}#{branch or 'main'}"
        hash_obj = hashlib.sha256(content.encode())
        hash_hex = hash_obj.hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{hash_hex}-{timestamp}"

    @staticmethod
    def validate_github_url(github_url: str) -> bool:
        """Validate GitHub URL format."""
        if github_url.endswith(".git"):
            github_url = github_url[:-4]
        
        if not github_url.startswith("https://github.com/"):
            return False
            
        parts = github_url.replace("https://github.com/", "").split("/")
        return len(parts) == 2

    @staticmethod
    def extract_repo_info(github_url: str) -> tuple[str, str]:
        """Extract owner and repo name from GitHub URL."""
        if github_url.endswith(".git"):
            github_url = github_url[:-4]
            
        if not github_url.startswith("https://github.com/"):
            raise ValueError("Invalid GitHub URL")
            
        parts = github_url.replace("https://github.com/", "").split("/")
        if len(parts) != 2:
            raise ValueError("Invalid GitHub URL format")
            
        return parts[0], parts[1]