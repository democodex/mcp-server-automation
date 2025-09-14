"""AWS cloud provider implementation."""

from typing import Dict, Any, Optional
from ..base import CloudProvider, ContainerRegistryOperations, DeploymentOperations
from .ecr_handler import ECRHandler
from .ecs_deployer import ECSDeployer


class AWSProvider(CloudProvider):
    """AWS cloud provider implementation."""

    def __init__(self, region: str, account_id: Optional[str] = None, **kwargs):
        super().__init__(region, account_id)
        self.account_id = account_id
        self._registry_ops = ECRHandler(region, account_id)
        self._deployment_ops = ECSDeployer(region, account_id)

    @property
    def name(self) -> str:
        """Get provider name."""
        return "aws"

    @property
    def registry_ops(self) -> ContainerRegistryOperations:
        """Get ECR operations."""
        return self._registry_ops

    @property
    def deployment_ops(self) -> DeploymentOperations:
        """Get ECS deployment operations."""
        return self._deployment_ops

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate AWS-specific configuration."""
        # Validate AWS-specific requirements
        if 'aws' not in config:
            raise ValueError("AWS configuration section is required")

        aws_config = config['aws']

        # Required fields
        required_fields = ['cluster_name', 'vpc_id', 'alb_subnet_ids', 'ecs_subnet_ids']
        for field in required_fields:
            if field not in aws_config:
                raise ValueError(f"AWS configuration missing required field: {field}")

        # Subnet validation
        alb_subnets = aws_config.get('alb_subnet_ids', [])
        ecs_subnets = aws_config.get('ecs_subnet_ids', [])

        if len(alb_subnets) < 2:
            raise ValueError("AWS ALB requires at least 2 subnet IDs in different Availability Zones")

        if len(ecs_subnets) < 1:
            raise ValueError("AWS ECS requires at least 1 subnet ID for task placement")

        # Certificate ARN validation (optional)
        cert_arn = aws_config.get('certificate_arn')
        if cert_arn and not cert_arn.startswith('arn:aws:acm:'):
            raise ValueError("Invalid certificate ARN format. Must start with 'arn:aws:acm:'")

        print("✅ AWS configuration validation passed")