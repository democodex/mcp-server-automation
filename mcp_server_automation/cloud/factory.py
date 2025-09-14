"""Cloud provider factory for creating provider instances."""

from typing import Optional, Dict, Any
from .base import CloudProvider


class CloudProviderFactory:
    """Factory class for creating cloud provider instances."""

    @staticmethod
    def create_provider(
        provider_type: str,
        region: str,
        project_id: Optional[str] = None,
        **kwargs: Any
    ) -> CloudProvider:
        """Create a cloud provider instance.

        Args:
            provider_type: Type of provider ('aws' or 'gcp')
            region: Cloud provider region
            project_id: Project/account ID (required for GCP)
            **kwargs: Additional provider-specific arguments

        Returns:
            CloudProvider instance

        Raises:
            ValueError: If provider type is unsupported
            ImportError: If provider dependencies are not installed
        """
        provider_type = provider_type.lower()

        if provider_type == 'aws':
            try:
                from .aws.provider import AWSProvider
                return AWSProvider(region=region, account_id=project_id, **kwargs)
            except ImportError as e:
                raise ImportError(
                    "AWS provider dependencies not installed. "
                    "Install with: pip install boto3"
                ) from e

        elif provider_type == 'gcp':
            if not project_id:
                raise ValueError("project_id is required for GCP provider")
            try:
                from .gcp.provider import GCPProvider
                return GCPProvider(region=region, project_id=project_id, **kwargs)
            except ImportError as e:
                raise ImportError(
                    "GCP provider dependencies not installed. "
                    "Install with: pip install google-cloud-run google-cloud-artifact-registry google-auth"
                ) from e

        else:
            raise ValueError(
                f"Unsupported provider type: {provider_type}. "
                f"Supported providers: aws, gcp"
            )

    @staticmethod
    def get_supported_providers() -> Dict[str, str]:
        """Get list of supported cloud providers.

        Returns:
            Dictionary mapping provider keys to display names
        """
        return {
            'aws': 'Amazon Web Services',
            'gcp': 'Google Cloud Platform'
        }

    @staticmethod
    def validate_provider_dependencies(provider_type: str) -> bool:
        """Check if provider dependencies are installed.

        Args:
            provider_type: Type of provider to check

        Returns:
            True if dependencies are available, False otherwise
        """
        provider_type = provider_type.lower()

        if provider_type == 'aws':
            try:
                import boto3
                return True
            except ImportError:
                return False

        elif provider_type == 'gcp':
            try:
                import google.cloud.run_v2
                import google.cloud.artifactregistry_v1
                import google.auth
                return True
            except ImportError:
                return False

        return False