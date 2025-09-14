"""Google Cloud Platform provider implementation."""

from typing import Dict, Any, Optional
from ..base import CloudProvider, ContainerRegistryOperations, DeploymentOperations
from .artifact_registry import ArtifactRegistryHandler
from .cloud_run_deployer import CloudRunDeployer


class GCPProvider(CloudProvider):
    """Google Cloud Platform provider implementation."""

    def __init__(self, region: str, project_id: str, **kwargs):
        super().__init__(region, project_id)
        if not project_id:
            raise ValueError("project_id is required for GCP provider")

        self._registry_ops = ArtifactRegistryHandler(region, project_id)
        self._deployment_ops = CloudRunDeployer(region, project_id)

    @property
    def name(self) -> str:
        """Get provider name."""
        return "gcp"

    @property
    def registry_ops(self) -> ContainerRegistryOperations:
        """Get Artifact Registry operations."""
        return self._registry_ops

    @property
    def deployment_ops(self) -> DeploymentOperations:
        """Get Cloud Run deployment operations."""
        return self._deployment_ops

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate GCP-specific configuration with detailed guidance."""
        try:
            # Validate GCP-specific requirements
            if 'gcp' not in config:
                raise ValueError(
                    "GCP configuration section is required.\n"
                    "Add 'gcp:' section to your config file with Cloud Run settings."
                )

            gcp_config = config['gcp']

            # Validate resource limits with detailed guidance
            cpu_limit = gcp_config.get('cpu_limit', '1000m')
            if not cpu_limit.endswith('m'):
                raise ValueError(
                    "CPU limit must be specified in millicores (e.g., '1000m').\n"
                    "Valid examples: '1000m' (1 CPU), '2000m' (2 CPUs), '500m' (0.5 CPU)"
                )

            memory_limit = gcp_config.get('memory_limit', '512Mi')
            if not (memory_limit.endswith('Mi') or memory_limit.endswith('Gi')):
                raise ValueError(
                    "Memory limit must be specified with Mi or Gi suffix.\n"
                    "Valid examples: '512Mi', '1Gi', '2Gi' (Max: 32Gi for Cloud Run)"
                )

            # Validate max instances with guidance
            max_instances = gcp_config.get('max_instances', 10)
            if not isinstance(max_instances, int) or max_instances < 1:
                raise ValueError(
                    "max_instances must be a positive integer.\n"
                    "Recommended: 10-100 for most workloads (Max: 1000 for Cloud Run)"
                )

            if max_instances > 1000:
                raise ValueError(
                    "max_instances cannot exceed 1000 (Cloud Run limit).\n"
                    "Contact Google Cloud support for higher limits if needed."
                )

            # Validate ingress setting with detailed options
            valid_ingress = ['all', 'internal', 'internal-and-cloud-load-balancing']
            ingress = gcp_config.get('ingress', 'all')
            if ingress not in valid_ingress:
                ingress_descriptions = {
                    'all': 'Public internet access',
                    'internal': 'VPC-internal access only',
                    'internal-and-cloud-load-balancing': 'VPC + Load Balancer access'
                }
                descriptions = [f"'{k}': {v}" for k, v in ingress_descriptions.items()]
                raise ValueError(
                    f"ingress must be one of: {', '.join(valid_ingress)}\n"
                    f"Options: {'; '.join(descriptions)}"
                )

            # Validate custom domain format with guidance
            custom_domain = gcp_config.get('custom_domain')
            if custom_domain:
                if not isinstance(custom_domain, str) or '.' not in custom_domain:
                    raise ValueError(
                        "custom_domain must be a valid domain name.\n"
                        "Example: 'myservice.example.com' (requires domain verification)"
                    )

            print("✅ GCP configuration validation passed")

        except Exception as e:
            # Enhance error messages with troubleshooting guidance
            enhanced_error = f"GCP Configuration Error: {str(e)}\n\n"
            enhanced_error += "🔧 GCP Troubleshooting Tips:\n"
            enhanced_error += "1. Verify gcloud CLI is configured: gcloud auth list\n"
            enhanced_error += "2. Check project ID is correct: gcloud config get-value project\n"
            enhanced_error += "3. Enable required APIs: Cloud Run, Artifact Registry\n"
            enhanced_error += "4. Ensure proper IAM permissions for Cloud Run Admin role\n"
            enhanced_error += "5. Verify region is valid: gcloud compute regions list"
            raise ValueError(enhanced_error)