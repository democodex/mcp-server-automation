"""Build module for MCP server automation."""

import os
import tempfile
from typing import Optional, List

from .config import ConfigLoader
from .dockerfile_generator import DockerfileGenerator
from .docker_handler import DockerHandler
from .github_handler import GitHubHandler
from .package_detector import PackageDetector


class BuildCommand:
    """Handles building and pushing MCP server Docker images."""

    def __init__(self):
        self.github_handler = GitHubHandler()
        self.package_detector = PackageDetector()
        self.dockerfile_generator = DockerfileGenerator()
        self.docker_handler = DockerHandler()

    def execute(
        self,
        github_url: Optional[str],
        subfolder: Optional[str],
        image_name: str,
        ecr_repository: str,
        aws_region: str,
        dockerfile_path: Optional[str],
        push_to_ecr: bool = True,
        branch: Optional[str] = None,
        command_override: Optional[List[str]] = None,
        environment_variables: Optional[dict] = None,
        entrypoint_command: Optional[str] = None,
        entrypoint_args: Optional[List[str]] = None,
        architecture: Optional[str] = None,
    ):
        """Execute the build process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Determine build mode
            is_entrypoint_mode = entrypoint_command is not None

            if is_entrypoint_mode:
                # For entrypoint mode, create a minimal directory structure
                mcp_server_path = temp_dir
                print(f"Building entrypoint command: {entrypoint_command} {' '.join(entrypoint_args or [])}")
            else:
                # Step 1: Fetch MCP server from GitHub
                if not github_url:
                    raise ValueError("github_url is required when not using entrypoint mode")
                mcp_server_path = self.github_handler.fetch_repository(
                    github_url, subfolder, temp_dir, branch
                )

            # Step 2: Detect package information
            package_info = self.package_detector.detect_package_info(
                mcp_server_path,
                command_override,
                environment_variables,
                github_url,
                subfolder,
                branch,
                entrypoint_command,
                entrypoint_args,
            )

            # Step 3: Generate Dockerfile
            dockerfile_content = self.dockerfile_generator.generate_dockerfile(
                package_info, dockerfile_path
            )
            dockerfile_full_path = os.path.join(temp_dir, "Dockerfile")
            with open(dockerfile_full_path, "w", encoding='utf-8') as f:
                f.write(dockerfile_content)

            # Step 4: Build Docker image
            # Generate appropriate tag based on mode
            if is_entrypoint_mode:
                dynamic_tag = ConfigLoader._generate_static_tag()
            else:
                if not github_url:
                    raise ValueError("github_url is required for GitHub mode")
                dynamic_tag = ConfigLoader._generate_dynamic_tag(github_url, branch)

            if push_to_ecr and ecr_repository:
                image_tag = f"{ecr_repository}/{image_name}:{dynamic_tag}"
            else:
                # Use local image name when not pushing to ECR
                image_tag = f"mcp-local/{image_name}:{dynamic_tag}"
            
            self.docker_handler.build_image(temp_dir, image_tag, mcp_server_path, architecture)

            # Step 5: Push to ECR (if enabled)
            if push_to_ecr:
                self.docker_handler.push_to_ecr(image_tag, aws_region)
            else:
                print(f"Skipping ECR push. Image built locally as: {image_tag}")