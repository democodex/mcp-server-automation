"""GitHub repository handling for MCP server automation."""

import os
import zipfile
from typing import Optional

import requests

from .utils import Utils


class GitHubHandler:
    """Handles fetching MCP servers from GitHub repositories."""

    def fetch_repository(
        self,
        github_url: str,
        subfolder: Optional[str],
        temp_dir: str,
        branch: Optional[str] = None,
    ) -> str:
        """Fetch MCP server from GitHub repository."""
        print(f"Fetching MCP server from {github_url}")

        # Validate and extract repo info
        if not Utils.validate_github_url(github_url):
            raise ValueError("Invalid GitHub URL")

        owner, repo = Utils.extract_repo_info(github_url)
        # Use specified branch or default to 'main'
        branch_name = branch if branch else "main"
        archive_url = (
            f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch_name}.zip"
        )

        if branch:
            print(f"Using branch: {branch}")
        else:
            print("Using default branch: main")

        # Download and extract
        response = requests.get(archive_url, timeout=60)
        response.raise_for_status()

        zip_path = os.path.join(temp_dir, "repo.zip")
        with open(zip_path, "wb") as f:
            f.write(response.content)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        # Find the extracted directory
        extracted_dirs = [
            d
            for d in os.listdir(temp_dir)
            if os.path.isdir(os.path.join(temp_dir, d)) and d != "__pycache__"
        ]
        if not extracted_dirs:
            raise RuntimeError("No directory found in extracted archive")

        repo_dir = os.path.join(temp_dir, extracted_dirs[0])

        # Handle subfolder
        if subfolder:
            mcp_server_path = os.path.join(repo_dir, subfolder)
            if not os.path.exists(mcp_server_path):
                raise RuntimeError(f"Subfolder '{subfolder}' not found in repository")
        else:
            mcp_server_path = repo_dir

        return mcp_server_path