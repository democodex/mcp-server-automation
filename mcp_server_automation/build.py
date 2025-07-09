"""Build module for MCP server automation."""

import os
import shutil
import tempfile
import re
import json
import toml
import base64
from typing import Optional, List

import requests
import zipfile
import boto3
import docker
from jinja2 import Template
from .config import ConfigLoader


class BuildCommand:
    """Handles building and pushing MCP server Docker images."""


    def __init__(self):
        self.docker_client = docker.from_env()

    def execute(
        self,
        github_url: str,
        subfolder: Optional[str],
        image_name: str,
        ecr_repository: str,
        aws_region: str,
        dockerfile_path: Optional[str],
        push_to_ecr: bool = True,
        branch: Optional[str] = None,
        command_override: Optional[List[str]] = None,
        environment_variables: Optional[dict] = None,
    ):
        """Execute the build process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Fetch MCP server from GitHub
            mcp_server_path = self._fetch_mcp_server(
                github_url, subfolder, temp_dir, branch
            )

            # Step 2: Generate Dockerfile
            dockerfile_content = self._generate_dockerfile(
                mcp_server_path,
                dockerfile_path,
                command_override,
                environment_variables,
                github_url,
                subfolder,
                branch,
            )
            dockerfile_full_path = os.path.join(temp_dir, "Dockerfile")
            with open(dockerfile_full_path, "w", encoding='utf-8') as f:
                f.write(dockerfile_content)

            # Step 3: Build Docker image
            # Generate dynamic tag
            dynamic_tag = ConfigLoader._generate_dynamic_tag(github_url, branch)

            if push_to_ecr and ecr_repository:
                image_tag = f"{ecr_repository}/{image_name}:{dynamic_tag}"
            else:
                # Use local image name when not pushing to ECR
                image_tag = f"mcp-local/{image_name}:{dynamic_tag}"
            self._build_docker_image(temp_dir, image_tag, mcp_server_path)

            # Step 4: Push to ECR (if enabled)
            if push_to_ecr:
                self._push_to_ecr(image_tag, aws_region)
            else:
                print(f"Skipping ECR push. Image built locally as: {image_tag}")

    def _fetch_mcp_server(
        self,
        github_url: str,
        subfolder: Optional[str],
        temp_dir: str,
        branch: Optional[str] = None,
    ) -> str:
        """Fetch MCP server from GitHub repository."""
        print(f"Fetching MCP server from {github_url}")

        # Convert GitHub URL to archive download URL
        if github_url.endswith(".git"):
            github_url = github_url[:-4]

        if not github_url.startswith("https://github.com/"):
            raise ValueError("Invalid GitHub URL")

        # Extract owner and repo from URL
        parts = github_url.replace("https://github.com/", "").split("/")
        if len(parts) != 2:
            raise ValueError("Invalid GitHub URL format")

        owner, repo = parts
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

    def _generate_dockerfile(
        self,
        mcp_server_path: str,
        custom_dockerfile_path: Optional[str],
        command_override: Optional[List[str]] = None,
        environment_variables: Optional[dict] = None,
        github_url: Optional[str] = None,
        subfolder: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> str:
        """Generate Dockerfile based on template."""
        if custom_dockerfile_path and os.path.exists(custom_dockerfile_path):
            with open(custom_dockerfile_path, "r", encoding='utf-8') as f:
                return f.read()

        # Detect package manager and dependencies  
        package_info = self._detect_package_info(
            mcp_server_path, command_override, environment_variables,
            github_url, subfolder, branch
        )

        # Load appropriate Dockerfile template based on language
        template_filename = f"Dockerfile-{package_info['language']}.j2"
        template_path = os.path.join(
            os.path.dirname(__file__), "templates", template_filename
        )
        with open(template_path, "r", encoding='utf-8') as f:
            template_content = f.read()

        dockerfile_template = Template(template_content)

        return dockerfile_template.render(package_info=package_info)

    def _detect_package_info(
        self,
        mcp_server_path: str,
        command_override: Optional[List[str]] = None,
        environment_variables: Optional[dict] = None,
        github_url: Optional[str] = None,
        subfolder: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> dict:
        """Detect package manager, dependency files, and start command."""
        # First detect the language/runtime
        language = self._detect_language(mcp_server_path)
        
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
        }

        # Priority 1: Use command override if provided
        if command_override:
            package_info["start_command"] = command_override
            print(f"Using command override: {' '.join(command_override)}")
        else:
            # Priority 2: Try to extract from README files first (most reliable)
            readme_command, has_docker_commands, has_any_commands = self._extract_start_command_from_readme(
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
                            self._extract_start_command_from_pyproject(content)
                        )

            elif os.path.exists(os.path.join(mcp_server_path, "requirements.txt")):
                package_info["requirements_file"] = "requirements.txt"

            elif os.path.exists(os.path.join(mcp_server_path, "setup.py")):
                package_info["project_file"] = "setup.py"
                if not package_info["start_command"]:
                    package_info["start_command"] = (
                        self._extract_start_command_from_setup_py(mcp_server_path)
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

        # Generate the complete ENTRYPOINT command
        package_info["entrypoint_command"] = self._generate_entrypoint_command(
            package_info["start_command"]
        )

        return package_info

    def _generate_entrypoint_command(
        self, start_command: Optional[List[str]]
    ) -> List[str]:
        """Generate the complete ENTRYPOINT command for mcp-proxy."""
        base_command = ["mcp-proxy", "--debug", "--port", "8000", "--shell"]

        if not start_command:
            return base_command + ["python", "-m", "server"]

        # Format: mcp-proxy --debug --port 8000 --shell <command> [-- <args>]
        if len(start_command) == 1:
            return base_command + start_command
        else:
            return base_command + [start_command[0]] + ["--"] + start_command[1:]

    def _extract_start_command_from_readme(
        self, mcp_server_path: str
    ) -> tuple[Optional[List[str]], bool, bool]:
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

    def _detect_language(self, mcp_server_path: str) -> str:
        """Detect the primary language/runtime of the MCP server."""
        # Check for Node.js indicators
        if os.path.exists(os.path.join(mcp_server_path, "package.json")):
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

    def _extract_start_command_from_pyproject(
        self, content: str
    ) -> Optional[List[str]]:
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

    def _extract_start_command_from_setup_py(
        self, mcp_server_path: str
    ) -> Optional[List[str]]:
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


    def _build_docker_image(
        self, build_context: str, image_tag: str, mcp_server_path: str
    ):
        """Build Docker image."""
        print(f"Building Docker image: {image_tag}")

        # Copy MCP server files to build context only if needed
        # (for cases where we can't install directly from repository)
        mcp_server_dest = os.path.join(build_context, "mcp-server")
        if os.path.exists(mcp_server_dest):
            shutil.rmtree(mcp_server_dest)
        
        # Always copy for now - the Dockerfile will decide whether to use it
        shutil.copytree(mcp_server_path, mcp_server_dest)

        # Build image
        self.docker_client.images.build(
            path=build_context, tag=image_tag, rm=True
        )

        print(f"Successfully built image: {image_tag}")

    def _push_to_ecr(self, image_tag: str, aws_region: str):
        """Push Docker image to ECR."""
        print(f"Pushing image to ECR: {image_tag}")

        # Initialize ECR client
        ecr_client = boto3.client("ecr", region_name=aws_region)

        # Extract full repository name from image tag
        # Format: 123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-servers/mcp-src-aws-documentation-mcp-server:latest
        # We need the full repository name including the image name part
        if ":" in image_tag:
            image_without_tag = image_tag.rsplit(":", 1)[0]
        else:
            image_without_tag = image_tag

        # Extract everything after the registry URL as the repository name
        registry_parts = image_without_tag.split("/")
        if len(registry_parts) >= 2:
            # Join everything after the registry URL (account.dkr.ecr.region.amazonaws.com)
            repo_name = "/".join(registry_parts[1:])
        else:
            repo_name = registry_parts[-1]

        # Create ECR repository if it doesn't exist
        try:
            ecr_client.describe_repositories(repositoryNames=[repo_name])
            print(f"ECR repository '{repo_name}' already exists")
        except ecr_client.exceptions.RepositoryNotFoundException:
            print(f"Creating ECR repository '{repo_name}'...")
            ecr_client.create_repository(
                repositoryName=repo_name,
                imageScanningConfiguration={"scanOnPush": True},
                encryptionConfiguration={"encryptionType": "AES256"},
            )
            print(f"ECR repository '{repo_name}' created successfully")

        # Get ECR login token
        token_response = ecr_client.get_authorization_token()
        token = token_response["authorizationData"][0]["authorizationToken"]
        endpoint = token_response["authorizationData"][0]["proxyEndpoint"]

        # Decode token
        username, password = base64.b64decode(token).decode().split(":")

        # Login to ECR
        self.docker_client.login(
            username=username, password=password, registry=endpoint
        )

        # Push image - use the full image_tag directly
        # Split image_tag into repository and tag parts
        if ":" in image_tag:
            repository, tag = image_tag.rsplit(":", 1)
        else:
            repository = image_tag
            tag = "latest"

        push_logs = self.docker_client.images.push(
            repository=repository, tag=tag, stream=True, decode=True
        )

        # Print push logs
        for log in push_logs:
            if "status" in log:
                print(f"{log['status']}: {log.get('progress', '')}")

        print(f"Successfully pushed image: {image_tag}")
