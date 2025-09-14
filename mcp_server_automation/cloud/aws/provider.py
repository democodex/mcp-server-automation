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
        """Validate AWS-specific configuration with detailed guidance."""
        try:
            # Validate AWS-specific requirements
            if 'aws' not in config:
                raise ValueError(
                    "AWS configuration section is required.\n"
                    "Add 'aws:' section to your config file with cluster_name, vpc_id, etc."
                )

            aws_config = config['aws']

            # Required fields with detailed guidance
            required_fields = {
                'cluster_name': 'ECS cluster name (create with: aws ecs create-cluster --cluster-name YOUR_CLUSTER)',
                'vpc_id': 'VPC ID where resources will be deployed (find with: aws ec2 describe-vpcs)',
                'alb_subnet_ids': 'Public subnet IDs for Application Load Balancer (minimum 2 in different AZs)',
                'ecs_subnet_ids': 'Private subnet IDs for ECS tasks (minimum 1)'
            }

            for field, guidance in required_fields.items():
                if field not in aws_config:
                    raise ValueError(
                        f"AWS configuration missing required field: {field}\n"
                        f"Description: {guidance}"
                    )

            # Subnet validation with specific guidance
            alb_subnets = aws_config.get('alb_subnet_ids', [])
            ecs_subnets = aws_config.get('ecs_subnet_ids', [])

            if len(alb_subnets) < 2:
                raise ValueError(
                    "AWS ALB requires at least 2 subnet IDs in different Availability Zones.\n"
                    "Find public subnets with: aws ec2 describe-subnets --filters 'Name=vpc-id,Values=YOUR_VPC_ID'"
                )

            if len(ecs_subnets) < 1:
                raise ValueError(
                    "AWS ECS requires at least 1 subnet ID for task placement.\n"
                    "Use private subnets for security. Find with: aws ec2 describe-subnets --filters 'Name=vpc-id,Values=YOUR_VPC_ID'"
                )

            # Certificate ARN validation (optional) with guidance
            cert_arn = aws_config.get('certificate_arn')
            if cert_arn and not cert_arn.startswith('arn:aws:acm:'):
                raise ValueError(
                    "Invalid certificate ARN format. Must start with 'arn:aws:acm:'\n"
                    "Find certificates with: aws acm list-certificates --region YOUR_REGION"
                )

            print("✅ AWS configuration validation passed")

        except Exception as e:
            # Enhance error messages with troubleshooting guidance
            enhanced_error = f"AWS Configuration Error: {str(e)}\n\n"
            enhanced_error += "🔧 AWS Troubleshooting Tips:\n"
            enhanced_error += "1. Verify AWS CLI is configured: aws sts get-caller-identity\n"
            enhanced_error += "2. Check your AWS region matches the resources\n"
            enhanced_error += "3. Ensure IAM permissions for ECS, ECR, CloudFormation, and EC2\n"
            enhanced_error += "4. Validate VPC and subnet IDs exist in your account"
            raise ValueError(enhanced_error)