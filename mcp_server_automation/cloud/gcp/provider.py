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
        """Validate GCP-specific configuration."""
        # Validate GCP-specific requirements
        if 'gcp' not in config:
            raise ValueError("GCP configuration section is required")

        gcp_config = config['gcp']

        # Validate resource limits
        cpu_limit = gcp_config.get('cpu_limit', '1000m')
        if not cpu_limit.endswith('m'):
            raise ValueError("CPU limit must be specified in millicores (e.g., '1000m')")

        memory_limit = gcp_config.get('memory_limit', '512Mi')
        if not (memory_limit.endswith('Mi') or memory_limit.endswith('Gi')):
            raise ValueError("Memory limit must be specified with Mi or Gi suffix (e.g., '512Mi')")

        # Validate max instances
        max_instances = gcp_config.get('max_instances', 10)
        if not isinstance(max_instances, int) or max_instances < 1:
            raise ValueError("max_instances must be a positive integer")

        # Validate ingress setting
        valid_ingress = ['all', 'internal', 'internal-and-cloud-load-balancing']
        ingress = gcp_config.get('ingress', 'all')
        if ingress not in valid_ingress:
            raise ValueError(f"ingress must be one of: {', '.join(valid_ingress)}")

        # Validate custom domain format (optional)
        custom_domain = gcp_config.get('custom_domain')
        if custom_domain:
            if not isinstance(custom_domain, str) or '.' not in custom_domain:
                raise ValueError("custom_domain must be a valid domain name")

        print("✅ GCP configuration validation passed")