"""Configuration management for MCP automation."""

import yaml
import boto3
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ImageConfig:
    """Configuration for Docker image."""
    
    repository: Optional[str] = None
    tag: Optional[str] = None


@dataclass
class EntrypointConfig:
    """Configuration for direct command entrypoint."""
    
    command: str
    args: Optional[list[str]] = None


@dataclass
class GitHubConfig:
    """Configuration for GitHub repository build."""
    
    github_url: str
    subfolder: Optional[str] = None
    branch: Optional[str] = None


@dataclass
class BuildConfig:
    """Configuration for build command."""

    # Either use entrypoint OR github, not both
    entrypoint: Optional[EntrypointConfig] = None
    github: Optional[GitHubConfig] = None
    
    image: Optional[ImageConfig] = None
    aws_region: str = "us-east-1"
    dockerfile_path: Optional[str] = None
    push_to_ecr: bool = False
    command_override: Optional[list[str]] = None
    environment_variables: Optional[Dict[str, str]] = None
    architecture: Optional[str] = None  # Platform/architecture for Docker build (e.g., "linux/amd64", "linux/arm64")
    
    # Computed properties
    @property
    def image_uri(self) -> Optional[str]:
        """Get the full image URI."""
        if self.image and self.image.repository:
            tag = self.image.tag or "latest"
            return f"{self.image.repository}:{tag}"
        return None
    
    @property 
    def image_name(self) -> str:
        """Get the image name from repository path or auto-generate it."""
        if self.image and self.image.repository:
            return self.image.repository.split("/")[-1]
        
        # Auto-generate image name based on build method
        if self.entrypoint:
            return ConfigLoader._generate_image_name_from_command(self.entrypoint.command)
        elif self.github:
            return ConfigLoader._generate_image_name(self.github.github_url, self.github.subfolder)
        else:
            return "mcp-server"
    
    @property
    def ecr_repository(self) -> Optional[str]:
        """Get the ECR repository base URL."""
        if self.image and self.image.repository and "/" in self.image.repository:
            return "/".join(self.image.repository.split("/")[:-1])
        return None


@dataclass
class DeployConfig:
    """Configuration for deploy command."""

    enabled: bool = False
    service_name: Optional[str] = None
    cluster_name: Optional[str] = None
    vpc_id: Optional[str] = None
    alb_subnet_ids: Optional[list[str]] = None  # Public subnets for ALB
    ecs_subnet_ids: Optional[list[str]] = None  # Private subnets for ECS tasks
    aws_region: str = "us-east-1"
    port: int = 8000
    cpu: int = 256
    memory: int = 512
    certificate_arn: Optional[str] = None
    save_config: Optional[str] = None


@dataclass
class MCPConfig:
    """Main configuration containing build and deploy configs."""

    build: Optional[BuildConfig] = None
    deploy: Optional[DeployConfig] = None


class ConfigLoader:
    """Loads and validates YAML configuration files."""

    @staticmethod
    def load_config(config_path: str) -> MCPConfig:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file, "r", encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        return ConfigLoader._parse_config(config_data)

    @staticmethod
    def _parse_config(config_data: Dict[str, Any]) -> MCPConfig:
        """Parse configuration data into MCPConfig."""
        build_config = None
        deploy_config = None

        if "build" in config_data:
            build_data = config_data["build"]
            aws_region = build_data.get("aws_region", ConfigLoader._get_aws_region())
            push_to_ecr = build_data.get("push_to_ecr", False)

            # Parse entrypoint configuration
            entrypoint_config = None
            if "entrypoint" in build_data:
                entrypoint_data = build_data["entrypoint"]
                entrypoint_config = EntrypointConfig(
                    command=entrypoint_data["command"],
                    args=entrypoint_data.get("args")
                )

            # Parse GitHub configuration (new format)
            github_config = None
            if "github" in build_data:
                github_data = build_data["github"]
                github_config = GitHubConfig(
                    github_url=github_data["github_url"],
                    subfolder=github_data.get("subfolder"),
                    branch=github_data.get("branch")
                )

            # Validate that only one method is specified
            if entrypoint_config and github_config:
                raise ValueError("Cannot specify both 'entrypoint' and 'github' in build configuration. Choose one method.")

            # Ensure at least one method is specified
            if not entrypoint_config and not github_config:
                raise ValueError("Must specify either 'entrypoint' for direct commands or 'github' for GitHub repositories in build configuration")

            # Handle image configuration
            image_config = None
            
            if "image" in build_data:
                # Use nested image structure if provided
                image_data = build_data["image"]
                repository = image_data.get("repository")
                tag = image_data.get("tag", "latest")
                
                if repository:
                    image_config = ImageConfig(repository=repository, tag=tag)
            
            elif push_to_ecr:
                # Auto-generate image configuration if pushing to ECR
                if github_config:
                    github_url = github_config.github_url
                    subfolder = github_config.subfolder
                    branch = github_config.branch
                    image_name = ConfigLoader._generate_image_name(github_url, subfolder)
                    tag = ConfigLoader._generate_dynamic_tag(github_url, branch)
                else:
                    # For entrypoint commands, use command as image name
                    image_name = ConfigLoader._generate_image_name_from_command(entrypoint_config.command)
                    tag = ConfigLoader._generate_static_tag()
                
                ecr_repository = ConfigLoader._generate_default_ecr_repository(aws_region)
                repository = f"{ecr_repository}/{image_name}"
                
                image_config = ImageConfig(repository=repository, tag=tag)

            build_config = BuildConfig(
                entrypoint=entrypoint_config,
                github=github_config,
                image=image_config,
                aws_region=aws_region,
                dockerfile_path=build_data.get("dockerfile_path"),
                push_to_ecr=push_to_ecr,
                command_override=build_data.get("command_override"),
                environment_variables=build_data.get("environment_variables"),
                architecture=build_data.get("architecture"),
            )

        if "deploy" in config_data:
            deploy_data = config_data["deploy"]
            enabled = deploy_data.get("enabled", False)

            # Handle subnet configuration
            alb_subnet_ids = None
            ecs_subnet_ids = None

            if "alb_subnet_ids" in deploy_data:
                alb_subnet_ids = deploy_data["alb_subnet_ids"]
                if isinstance(alb_subnet_ids, str):
                    alb_subnet_ids = [s.strip() for s in alb_subnet_ids.split(",")]

            if "ecs_subnet_ids" in deploy_data:
                ecs_subnet_ids = deploy_data["ecs_subnet_ids"]
                if isinstance(ecs_subnet_ids, str):
                    ecs_subnet_ids = [s.strip() for s in ecs_subnet_ids.split(",")]

            deploy_config = DeployConfig(
                enabled=enabled,
                service_name=deploy_data.get("service_name"),
                cluster_name=deploy_data.get("cluster_name"),
                vpc_id=deploy_data.get("vpc_id"),
                alb_subnet_ids=alb_subnet_ids,
                ecs_subnet_ids=ecs_subnet_ids,
                aws_region=deploy_data.get(
                    "aws_region", ConfigLoader._get_aws_region()
                ),
                port=deploy_data.get("port", 8000),
                cpu=deploy_data.get("cpu", 256),
                memory=deploy_data.get("memory", 512),
                certificate_arn=deploy_data.get("certificate_arn"),
                save_config=deploy_data.get("save_config"),
            )

        return MCPConfig(build=build_config, deploy=deploy_config)

    @staticmethod
    def _generate_image_name(github_url: str, subfolder: Optional[str] = None) -> str:
        """Generate simple image name from GitHub URL."""
        repo_name = github_url.rstrip(".git").split("/")[-1]
        if subfolder:
            subfolder_name = subfolder.strip("/").replace("/", "-")
            return f"{repo_name}-{subfolder_name}"
        return repo_name

    @staticmethod
    def _get_aws_region() -> str:
        """Get AWS region from profile or default to us-east-1."""
        try:
            session = boto3.Session()
            return session.region_name or "us-east-1"
        except Exception:
            return "us-east-1"

    @staticmethod 
    def _generate_dynamic_tag(github_url: str, branch: Optional[str] = None) -> str:
        """Generate dynamic image tag using GitHub API commit hash and timestamp."""
        import requests
        from datetime import datetime
        
        try:
            # Extract owner and repo from GitHub URL
            parts = github_url.replace("https://github.com/", "").split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                branch_ref = branch if branch else "HEAD"
                api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch_ref}"
                response = requests.get(api_url, timeout=30)
                if response.status_code == 200:
                    commit_data = response.json()
                    git_hash = commit_data["sha"][:8]
                else:
                    git_hash = "nocommit"
            else:
                git_hash = "nocommit"
        except Exception:
            git_hash = "nocommit"

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if branch:
            return f"{git_hash}-{branch}-{timestamp}"
        else:
            return f"{git_hash}-{timestamp}"


    @staticmethod
    def _generate_image_name_from_command(command: str) -> str:
        """Generate image name from command for entrypoint mode."""
        # Clean up command to make it a valid image name
        import re
        # Remove common prefixes and clean up the command
        clean_command = command.replace("@", "").replace("/", "-").replace(".", "-")
        # Remove any invalid characters and make lowercase
        clean_command = re.sub(r'[^a-zA-Z0-9\-_]', '', clean_command).lower()
        return f"mcp-{clean_command}"

    @staticmethod
    def _generate_static_tag() -> str:
        """Generate static tag for entrypoint commands."""
        from .utils import Utils
        return Utils.generate_static_tag()

    @staticmethod
    def _generate_default_ecr_repository(aws_region: str) -> str:
        """Generate default ECR repository URI using AWS account ID."""
        sts_client = boto3.client("sts", region_name=aws_region)
        account_id = sts_client.get_caller_identity()["Account"]
        return f"{account_id}.dkr.ecr.{aws_region}.amazonaws.com/mcp-servers"
