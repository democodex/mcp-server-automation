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
                error_msg = (
                    "❌ AWS provider dependencies not installed.\n\n"
                    "🔧 Installation Options:\n"
                    "  • From source: pip install -e \".[aws]\"\n"
                    "  • Multi-cloud: pip install -e \".[all]\"\n"
                    "  • Manual: pip install boto3 botocore\n\n"
                    "📋 Required AWS Setup:\n"
                    "  1. Configure AWS CLI: aws configure\n"
                    "  2. Verify access: aws sts get-caller-identity\n"
                    "  3. Set default region: aws configure set region us-east-1"
                )
                raise ImportError(error_msg) from e

        elif provider_type == 'gcp':
            if not project_id:
                raise ValueError(
                    "project_id is required for GCP provider.\n"
                    "Specify with: --project-id YOUR_PROJECT_ID or in config file"
                )
            try:
                from .gcp.provider import GCPProvider
                return GCPProvider(region=region, project_id=project_id, **kwargs)
            except ImportError as e:
                error_msg = (
                    "❌ GCP provider dependencies not installed.\n\n"
                    "🔧 Installation Options:\n"
                    "  • From source: pip install -e \".[gcp]\"\n"
                    "  • Multi-cloud: pip install -e \".[all]\"\n"
                    "  • Manual: pip install google-cloud-run google-cloud-artifact-registry google-auth\n\n"
                    "📋 Required GCP Setup:\n"
                    "  1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install\n"
                    "  2. Authenticate: gcloud auth login\n"
                    "  3. Set project: gcloud config set project YOUR_PROJECT_ID\n"
                    "  4. Enable APIs: gcloud services enable run.googleapis.com artifactregistry.googleapis.com"
                )
                raise ImportError(error_msg) from e

        else:
            supported = list(CloudProviderFactory.get_supported_providers().keys())
            raise ValueError(
                f"❌ Unsupported provider type: '{provider_type}'\n\n"
                f"✅ Supported providers: {', '.join(supported)}\n\n"
                f"💡 Usage examples:\n"
                f"  • AWS: --provider aws\n"
                f"  • GCP: --provider gcp --project-id YOUR_PROJECT"
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