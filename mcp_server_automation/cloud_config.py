"""Multi-cloud configuration management for MCP automation."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import os.path
import re

# Import existing config classes for backward compatibility
from .config import EntrypointConfig, GitHubConfig, ImageConfig, ConfigLoader


@dataclass
class CloudConfig:
    """Configuration for cloud provider settings."""

    provider: str  # 'aws' or 'gcp'
    region: str
    project_id: Optional[str] = None  # GCP project ID / AWS account ID

    def __post_init__(self):
        """Validate cloud configuration after initialization."""
        if self.provider not in ['aws', 'gcp']:
            raise ValueError(f"Unsupported provider: {self.provider}. Must be 'aws' or 'gcp'")

        if self.provider == 'gcp' and not self.project_id:
            raise ValueError("project_id is required for GCP provider")


@dataclass
class ContainerRegistryConfig:
    """Configuration for container registry operations."""

    provider: str
    registry_url: Optional[str] = None  # Auto-generated if None
    repository_name: str = "mcp-servers"

    def get_registry_url(self, cloud_config: CloudConfig) -> str:
        """Get the registry URL for the cloud provider."""
        if self.registry_url:
            return self.registry_url

        if cloud_config.provider == 'aws':
            # Use existing ECR URL generation logic
            return ConfigLoader._generate_default_ecr_repository(cloud_config.region)
        elif cloud_config.provider == 'gcp':
            # Generate Artifact Registry URL
            return f"{cloud_config.region}-docker.pkg.dev/{cloud_config.project_id}"
        else:
            raise ValueError(f"Unsupported provider: {cloud_config.provider}")


@dataclass
class MultiCloudBuildConfig:
    """Multi-cloud build configuration."""

    # Build method (either entrypoint OR github, not both)
    entrypoint: Optional[EntrypointConfig] = None
    github: Optional[GitHubConfig] = None

    # Registry configuration
    push_to_registry: bool = False  # Renamed from push_to_ecr
    registry: Optional[ContainerRegistryConfig] = None

    # Docker configuration
    dockerfile_path: Optional[str] = None
    architecture: Optional[str] = None
    environment_variables: Optional[Dict[str, str]] = None
    command_override: Optional[list[str]] = None

    # Image configuration
    image: Optional[ImageConfig] = None

    def __post_init__(self):
        """Validate build configuration after initialization."""
        # Validate that only one build method is specified
        if self.entrypoint and self.github:
            raise ValueError("Cannot specify both 'entrypoint' and 'github'. Choose one method.")

        if not self.entrypoint and not self.github:
            raise ValueError("Must specify either 'entrypoint' or 'github' build method")

        # Initialize registry config if needed
        if not self.registry:
            self.registry = ContainerRegistryConfig(provider="aws")  # Default to AWS for compatibility


@dataclass
class AWSDeployConfig:
    """AWS-specific deployment configuration."""

    cluster_name: str
    vpc_id: str
    alb_subnet_ids: list[str]  # Public subnets for ALB (minimum 2)
    ecs_subnet_ids: list[str]  # Private subnets for ECS tasks (minimum 1)
    certificate_arn: Optional[str] = None


@dataclass
class GCPDeployConfig:
    """GCP-specific deployment configuration."""

    allow_unauthenticated: bool = True  # Public Cloud Run service
    max_instances: int = 10
    cpu_limit: str = "1000m"  # CPU limit (e.g., "1000m" = 1 CPU)
    memory_limit: str = "512Mi"  # Memory limit (e.g., "512Mi" = 512 MB)
    custom_domain: Optional[str] = None  # Custom domain for service
    ingress: str = "all"  # Traffic ingress ('all', 'internal', 'internal-and-cloud-load-balancing')


@dataclass
class MultiCloudDeployConfig:
    """Multi-cloud deployment configuration."""

    enabled: bool = False
    service_name: str
    port: int = 8000

    # Cloud-specific configurations
    aws: Optional[AWSDeployConfig] = None
    gcp: Optional[GCPDeployConfig] = None

    # Common settings
    save_config: Optional[str] = None  # Path to save MCP client config

    def get_cloud_config(self, provider: str) -> Union[AWSDeployConfig, GCPDeployConfig]:
        """Get cloud-specific deployment configuration."""
        if provider == 'aws':
            if not self.aws:
                raise ValueError("AWS deployment configuration is required when using AWS provider")
            return self.aws
        elif provider == 'gcp':
            if not self.gcp:
                raise ValueError("GCP deployment configuration is required when using GCP provider")
            return self.gcp
        else:
            raise ValueError(f"Unsupported provider: {provider}")


@dataclass
class MultiCloudMCPConfig:
    """Main multi-cloud configuration containing cloud, build and deploy configs."""

    cloud: CloudConfig
    build: Optional[MultiCloudBuildConfig] = None
    deploy: Optional[MultiCloudDeployConfig] = None

    # Legacy compatibility - these will be derived from cloud config
    @property
    def region(self) -> str:
        """Get region for backward compatibility."""
        return self.cloud.region

    @property
    def provider(self) -> str:
        """Get provider name."""
        return self.cloud.provider


class MultiCloudConfigLoader:
    """Loads and validates multi-cloud YAML configuration files."""

    @staticmethod
    def load_config(config_path: str) -> MultiCloudMCPConfig:
        """Load multi-cloud configuration from YAML file."""
        # Validate path to prevent traversal
        safe_path = ConfigLoader._validate_path(config_path)
        config_file = Path(safe_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file, "r", encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        return MultiCloudConfigLoader._parse_config(config_data)

    @staticmethod
    def _parse_config(config_data: Dict[str, Any]) -> MultiCloudMCPConfig:
        """Parse configuration data into MultiCloudMCPConfig."""
        # Parse cloud configuration
        cloud_config = MultiCloudConfigLoader._parse_cloud_config(config_data)

        # Parse build configuration
        build_config = None
        if "build" in config_data:
            build_config = MultiCloudConfigLoader._parse_build_config(
                config_data["build"], cloud_config
            )

        # Parse deploy configuration
        deploy_config = None
        if "deploy" in config_data:
            deploy_config = MultiCloudConfigLoader._parse_deploy_config(
                config_data["deploy"], cloud_config
            )

        return MultiCloudMCPConfig(
            cloud=cloud_config,
            build=build_config,
            deploy=deploy_config
        )

    @staticmethod
    def _parse_cloud_config(config_data: Dict[str, Any]) -> CloudConfig:
        """Parse cloud provider configuration."""
        if "cloud" in config_data:
            cloud_data = config_data["cloud"]
            return CloudConfig(
                provider=cloud_data["provider"],
                region=cloud_data["region"],
                project_id=cloud_data.get("project_id")
            )
        else:
            # Backward compatibility - derive from build section
            build_data = config_data.get("build", {})
            aws_region = build_data.get("aws_region", "us-east-1")

            # Default to AWS for backward compatibility
            return CloudConfig(
                provider="aws",
                region=aws_region,
                project_id=None
            )

    @staticmethod
    def _parse_build_config(
        build_data: Dict[str, Any],
        cloud_config: CloudConfig
    ) -> MultiCloudBuildConfig:
        """Parse build configuration."""
        # Parse entrypoint configuration
        entrypoint_config = None
        if "entrypoint" in build_data:
            entrypoint_data = build_data["entrypoint"]
            entrypoint_config = EntrypointConfig(
                command=entrypoint_data["command"],
                args=entrypoint_data.get("args")
            )

        # Parse GitHub configuration
        github_config = None
        if "github" in build_data:
            github_data = build_data["github"]
            github_url = ConfigLoader._validate_github_url(github_data["github_url"])
            github_config = GitHubConfig(
                github_url=github_url,
                subfolder=ConfigLoader._sanitize_string(github_data.get("subfolder")),
                branch=ConfigLoader._sanitize_string(github_data.get("branch"))
            )

        # Parse registry configuration
        push_to_registry = build_data.get("push_to_registry", False)
        # Backward compatibility
        if "push_to_ecr" in build_data:
            push_to_registry = build_data["push_to_ecr"]

        registry_config = ContainerRegistryConfig(
            provider=cloud_config.provider,
            repository_name=build_data.get("repository_name", "mcp-servers")
        )

        # Handle image configuration
        image_config = None
        if "image" in build_data:
            image_data = build_data["image"]
            image_config = ImageConfig(
                repository=image_data.get("repository"),
                tag=image_data.get("tag", "latest")
            )

        return MultiCloudBuildConfig(
            entrypoint=entrypoint_config,
            github=github_config,
            push_to_registry=push_to_registry,
            registry=registry_config,
            dockerfile_path=ConfigLoader._sanitize_string(build_data.get("dockerfile_path")),
            architecture=ConfigLoader._sanitize_string(build_data.get("architecture")),
            environment_variables=ConfigLoader._sanitize_env_vars(build_data.get("environment_variables")),
            command_override=ConfigLoader._sanitize_command_list(build_data.get("command_override")),
            image=image_config
        )

    @staticmethod
    def _parse_deploy_config(
        deploy_data: Dict[str, Any],
        cloud_config: CloudConfig
    ) -> MultiCloudDeployConfig:
        """Parse deployment configuration."""
        enabled = deploy_data.get("enabled", False)
        service_name = deploy_data.get("service_name")
        if not service_name:
            raise ValueError("service_name is required in deploy configuration")

        # Parse cloud-specific deployment configs
        aws_config = None
        gcp_config = None

        if "aws" in deploy_data:
            aws_data = deploy_data["aws"]

            # Handle subnet configuration
            alb_subnet_ids = aws_data.get("alb_subnet_ids", [])
            if isinstance(alb_subnet_ids, str):
                alb_subnet_ids = [s.strip() for s in alb_subnet_ids.split(",")]

            ecs_subnet_ids = aws_data.get("ecs_subnet_ids", [])
            if isinstance(ecs_subnet_ids, str):
                ecs_subnet_ids = [s.strip() for s in ecs_subnet_ids.split(",")]

            aws_config = AWSDeployConfig(
                cluster_name=aws_data["cluster_name"],
                vpc_id=aws_data["vpc_id"],
                alb_subnet_ids=alb_subnet_ids,
                ecs_subnet_ids=ecs_subnet_ids,
                certificate_arn=ConfigLoader._sanitize_string(aws_data.get("certificate_arn"))
            )

        if "gcp" in deploy_data:
            gcp_data = deploy_data["gcp"]
            gcp_config = GCPDeployConfig(
                allow_unauthenticated=gcp_data.get("allow_unauthenticated", True),
                max_instances=gcp_data.get("max_instances", 10),
                cpu_limit=gcp_data.get("cpu_limit", "1000m"),
                memory_limit=gcp_data.get("memory_limit", "512Mi"),
                custom_domain=ConfigLoader._sanitize_string(gcp_data.get("custom_domain")),
                ingress=gcp_data.get("ingress", "all")
            )

        # Backward compatibility - if no cloud-specific config, use legacy format
        if not aws_config and not gcp_config and cloud_config.provider == "aws":
            # Handle legacy AWS configuration format
            alb_subnet_ids = deploy_data.get("alb_subnet_ids", [])
            if isinstance(alb_subnet_ids, str):
                alb_subnet_ids = [s.strip() for s in alb_subnet_ids.split(",")]

            ecs_subnet_ids = deploy_data.get("ecs_subnet_ids", [])
            if isinstance(ecs_subnet_ids, str):
                ecs_subnet_ids = [s.strip() for s in ecs_subnet_ids.split(",")]

            aws_config = AWSDeployConfig(
                cluster_name=deploy_data.get("cluster_name", ""),
                vpc_id=deploy_data.get("vpc_id", ""),
                alb_subnet_ids=alb_subnet_ids,
                ecs_subnet_ids=ecs_subnet_ids,
                certificate_arn=ConfigLoader._sanitize_string(deploy_data.get("certificate_arn"))
            )

        return MultiCloudDeployConfig(
            enabled=enabled,
            service_name=service_name,
            port=deploy_data.get("port", 8000),
            aws=aws_config,
            gcp=gcp_config,
            save_config=ConfigLoader._sanitize_string(deploy_data.get("save_config"))
        )