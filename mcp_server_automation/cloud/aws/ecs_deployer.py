"""AWS ECS (Elastic Container Service) deployment operations."""

import os
import html
from typing import Optional
import boto3
from jinja2.sandbox import SandboxedEnvironment
from ..base import DeploymentOperations, DeploymentResult


class ECSDeployer(DeploymentOperations):
    """Handles AWS ECS deployment with CloudFormation."""

    def __init__(self, region: str, account_id: Optional[str] = None):
        self.region = region
        self.account_id = account_id
        self.cf_client = None

    def _get_cf_client(self):
        """Get or create CloudFormation client."""
        if not self.cf_client:
            self.cf_client = boto3.client("cloudformation", region_name=self.region)
        return self.cf_client

    def deploy_service(self, config) -> DeploymentResult:
        """Deploy service to ECS using CloudFormation."""
        from ...cloud_config import MultiCloudDeployConfig

        # Extract AWS-specific configuration
        aws_config = config.get_cloud_config('aws')

        # Generate CloudFormation template
        cf_template = self._generate_cloudformation_template(
            image_uri=config.image_uri,
            service_name=config.service_name,
            cluster_name=aws_config.cluster_name,
            port=config.port,
            cpu=config.cpu or 256,
            memory=config.memory or 512,
            vpc_id=aws_config.vpc_id,
            alb_subnet_ids=aws_config.alb_subnet_ids,
            ecs_subnet_ids=aws_config.ecs_subnet_ids,
            certificate_arn=aws_config.certificate_arn,
        )

        # Deploy CloudFormation stack
        stack_name = f"mcp-server-{config.service_name}"
        alb_url = self._deploy_cloudformation_stack(
            cf_template,
            stack_name,
            config.service_name,
            aws_config.vpc_id,
            aws_config.alb_subnet_ids,
            aws_config.ecs_subnet_ids,
            aws_config.certificate_arn,
        )

        return DeploymentResult(
            service_url=alb_url,
            service_name=config.service_name,
            deployment_info={
                "stack_name": stack_name,
                "region": self.region,
                "cluster_name": aws_config.cluster_name,
                "vpc_id": aws_config.vpc_id,
            }
        )

    def get_service_url(self, service_name: str) -> str:
        """Get ALB URL for deployed ECS service."""
        stack_name = f"mcp-server-{service_name}"
        cf_client = self._get_cf_client()

        try:
            stack_info = cf_client.describe_stacks(StackName=stack_name)
            outputs = stack_info["Stacks"][0].get("Outputs", [])

            for output in outputs:
                if output["OutputKey"] == "ALBUrl":
                    return output["OutputValue"]

            raise RuntimeError(f"ALB URL not found in stack outputs for service: {service_name}")
        except cf_client.exceptions.ClientError as e:
            if "does not exist" in str(e):
                raise RuntimeError(f"ECS service '{service_name}' not found")
            raise

    def delete_service(self, service_name: str) -> None:
        """Delete ECS service by deleting CloudFormation stack."""
        stack_name = f"mcp-server-{service_name}"
        cf_client = self._get_cf_client()

        try:
            print(f"Deleting CloudFormation stack: {stack_name}")
            cf_client.delete_stack(StackName=stack_name)

            print("Waiting for stack deletion to complete...")
            waiter = cf_client.get_waiter("stack_delete_complete")
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={
                    "Delay": 30,
                    "MaxAttempts": 120,  # Wait up to 60 minutes
                },
            )
            print(f"✅ Successfully deleted ECS service: {service_name}")
        except cf_client.exceptions.ClientError as e:
            if "does not exist" in str(e):
                print(f"Stack {stack_name} does not exist, nothing to delete")
            else:
                raise

    def _generate_cloudformation_template(
        self,
        image_uri: str,
        service_name: str,
        cluster_name: str,
        port: int,
        cpu: int,
        memory: int,
        vpc_id: str,
        alb_subnet_ids: list,
        ecs_subnet_ids: list,
        certificate_arn: Optional[str],
    ) -> str:
        """Generate CloudFormation template for ECS deployment."""

        # Load CloudFormation template
        template_path = os.path.join(
            os.path.dirname(__file__), "templates", "ecs-service.yaml"
        )
        with open(template_path, "r", encoding='utf-8') as f:
            template_content = f.read()

        # Use sandboxed environment and sanitize inputs
        env = SandboxedEnvironment()
        template = env.from_string(template_content)
        return template.render(
            service_name=html.escape(str(service_name)),
            cluster_name=html.escape(str(cluster_name)),
            image_uri=html.escape(str(image_uri)),
            port=int(port),
            cpu=int(cpu),
            memory=int(memory),
        )

    def _deploy_cloudformation_stack(
        self,
        template: str,
        stack_name: str,
        service_name: str,
        vpc_id: str,
        alb_subnet_ids: list,
        ecs_subnet_ids: list,
        certificate_arn: Optional[str],
    ) -> str:
        """Deploy CloudFormation stack and return ALB URL."""
        print(f"Deploying CloudFormation stack: {stack_name}")

        cf_client = self._get_cf_client()

        # Check if stack exists
        try:
            cf_client.describe_stacks(StackName=stack_name)
            stack_exists = True
        except cf_client.exceptions.ClientError:
            stack_exists = False

        # Prepare parameters
        parameters = [
            {"ParameterKey": "ServiceName", "ParameterValue": service_name},
            {"ParameterKey": "VpcId", "ParameterValue": vpc_id},
            {
                "ParameterKey": "ALBSubnetIds",
                "ParameterValue": ",".join(alb_subnet_ids),
            },
            {
                "ParameterKey": "ECSSubnetIds",
                "ParameterValue": ",".join(ecs_subnet_ids),
            },
        ]

        if certificate_arn:
            parameters.append(
                {"ParameterKey": "CertificateArn", "ParameterValue": certificate_arn}
            )

        if stack_exists:
            print("Updating existing stack...")
            try:
                cf_client.update_stack(
                    StackName=stack_name,
                    TemplateBody=template,
                    Parameters=parameters,
                    Capabilities=["CAPABILITY_NAMED_IAM"],
                )
                waiter = cf_client.get_waiter("stack_update_complete")
            except cf_client.exceptions.ClientError as e:
                if "No updates are to be performed" in str(e):
                    print("No updates needed - stack is already up to date")
                    waiter = None
                else:
                    raise
        else:
            print("Creating new stack...")
            cf_client.create_stack(
                StackName=stack_name,
                TemplateBody=template,
                Parameters=parameters,
                Capabilities=["CAPABILITY_NAMED_IAM"],
            )
            waiter = cf_client.get_waiter("stack_create_complete")

        # Wait for stack operation to complete with extended timeout
        if waiter:
            print("Waiting for stack operation to complete...")
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={
                    "Delay": 30,  # Check every 30 seconds
                    "MaxAttempts": 120,  # Wait up to 60 minutes (120 * 30 seconds)
                },
            )

        # Get ALB URL from stack outputs
        stack_info = cf_client.describe_stacks(StackName=stack_name)
        outputs = stack_info["Stacks"][0].get("Outputs", [])

        for output in outputs:
            if output["OutputKey"] == "ALBUrl":
                print("Stack deployment completed successfully")
                return output["OutputValue"]

        raise RuntimeError("ALB URL not found in stack outputs")