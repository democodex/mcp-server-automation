"""Abstract base classes for cloud provider operations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..cloud_config import MultiCloudDeployConfig, MultiCloudBuildConfig


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    service_url: str
    service_name: str
    deployment_info: Dict[str, Any]


@dataclass
class RegistryResult:
    """Result of container registry operations."""
    image_uri: str
    registry_url: str
    repository_name: str


class ContainerRegistryOperations(ABC):
    """Abstract interface for container registry operations."""

    @abstractmethod
    def build_registry_url(self, project_id: Optional[str] = None) -> str:
        """Build the registry URL for the cloud provider.

        Args:
            project_id: Cloud provider project/account ID

        Returns:
            Complete registry URL
        """
        pass

    @abstractmethod
    def authenticate(self) -> None:
        """Authenticate with the container registry."""
        pass

    @abstractmethod
    def push_image(self, image_tag: str, local_tag: str) -> RegistryResult:
        """Push image to container registry.

        Args:
            image_tag: Target image tag in registry
            local_tag: Local image tag to push

        Returns:
            Registry operation result
        """
        pass

    @abstractmethod
    def create_repository_if_needed(self, repo_name: str) -> None:
        """Create repository if it doesn't exist.

        Args:
            repo_name: Repository name to create
        """
        pass


class DeploymentOperations(ABC):
    """Abstract interface for container deployment operations."""

    @abstractmethod
    def deploy_service(self, config: 'MultiCloudDeployConfig') -> DeploymentResult:
        """Deploy container service to cloud platform.

        Args:
            config: Deployment configuration

        Returns:
            Deployment operation result
        """
        pass

    @abstractmethod
    def get_service_url(self, service_name: str) -> str:
        """Get the public URL for a deployed service.

        Args:
            service_name: Name of the deployed service

        Returns:
            Public URL for the service
        """
        pass

    @abstractmethod
    def delete_service(self, service_name: str) -> None:
        """Delete a deployed service.

        Args:
            service_name: Name of the service to delete
        """
        pass


class CloudProvider(ABC):
    """Abstract base class for cloud provider implementations."""

    def __init__(self, region: str, project_id: Optional[str] = None):
        """Initialize cloud provider.

        Args:
            region: Cloud provider region
            project_id: Project/account ID (GCP project ID, AWS account ID)
        """
        self.region = region
        self.project_id = project_id

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the provider name."""
        pass

    @property
    @abstractmethod
    def registry_ops(self) -> ContainerRegistryOperations:
        """Get container registry operations."""
        pass

    @property
    @abstractmethod
    def deployment_ops(self) -> DeploymentOperations:
        """Get deployment operations."""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate provider-specific configuration.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    def deploy_container_service(self, config: 'MultiCloudDeployConfig') -> DeploymentResult:
        """High-level method to deploy container service.

        Args:
            config: Deployment configuration

        Returns:
            Deployment result with service URL and metadata
        """
        return self.deployment_ops.deploy_service(config)

    def push_container_image(self, image_tag: str, local_tag: str, config: 'MultiCloudBuildConfig') -> RegistryResult:
        """High-level method to push container image.

        Args:
            image_tag: Target image tag in registry
            local_tag: Local image tag to push
            config: Build configuration

        Returns:
            Registry result with image URI and metadata
        """
        return self.registry_ops.push_image(image_tag, local_tag)