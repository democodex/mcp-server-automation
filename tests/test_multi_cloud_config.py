"""Tests for multi-cloud configuration."""

import unittest
import tempfile
import os
from mcp_server_automation.cloud_config import (
    MultiCloudConfigLoader, CloudConfig, MultiCloudBuildConfig,
    MultiCloudDeployConfig, AWSDeployConfig, GCPDeployConfig
)


class TestMultiCloudConfig(unittest.TestCase):
    """Test cases for multi-cloud configuration."""

    def test_cloud_config_aws(self):
        """Test CloudConfig with AWS provider."""
        config = CloudConfig(provider="aws", region="us-east-1")
        self.assertEqual(config.provider, "aws")
        self.assertEqual(config.region, "us-east-1")
        self.assertIsNone(config.project_id)

    def test_cloud_config_gcp(self):
        """Test CloudConfig with GCP provider."""
        config = CloudConfig(provider="gcp", region="us-central1", project_id="my-project")
        self.assertEqual(config.provider, "gcp")
        self.assertEqual(config.region, "us-central1")
        self.assertEqual(config.project_id, "my-project")

    def test_cloud_config_invalid_provider(self):
        """Test CloudConfig with invalid provider."""
        with self.assertRaises(ValueError) as context:
            CloudConfig(provider="azure", region="eastus")
        self.assertIn("Unsupported provider: azure", str(context.exception))

    def test_cloud_config_gcp_missing_project_id(self):
        """Test CloudConfig with GCP but missing project_id."""
        with self.assertRaises(ValueError) as context:
            CloudConfig(provider="gcp", region="us-central1")
        self.assertIn("project_id is required for GCP provider", str(context.exception))

    def test_aws_deploy_config(self):
        """Test AWS deployment configuration."""
        aws_config = AWSDeployConfig(
            cluster_name="test-cluster",
            vpc_id="vpc-123456",
            alb_subnet_ids=["subnet-1", "subnet-2"],
            ecs_subnet_ids=["subnet-3"],
            certificate_arn="arn:aws:acm:us-east-1:123456789012:certificate/test"
        )
        self.assertEqual(aws_config.cluster_name, "test-cluster")
        self.assertEqual(aws_config.vpc_id, "vpc-123456")
        self.assertEqual(len(aws_config.alb_subnet_ids), 2)
        self.assertEqual(len(aws_config.ecs_subnet_ids), 1)

    def test_gcp_deploy_config(self):
        """Test GCP deployment configuration."""
        gcp_config = GCPDeployConfig(
            allow_unauthenticated=True,
            max_instances=20,
            cpu_limit="2000m",
            memory_limit="2Gi",
            custom_domain="mcp.example.com"
        )
        self.assertTrue(gcp_config.allow_unauthenticated)
        self.assertEqual(gcp_config.max_instances, 20)
        self.assertEqual(gcp_config.cpu_limit, "2000m")
        self.assertEqual(gcp_config.memory_limit, "2Gi")
        self.assertEqual(gcp_config.custom_domain, "mcp.example.com")

    def test_load_gcp_config_from_yaml(self):
        """Test loading GCP configuration from YAML."""
        yaml_content = """
cloud:
  provider: "gcp"
  region: "us-central1"
  project_id: "test-project"

build:
  entrypoint:
    command: "uvx"
    args: ["mcp-server"]
  push_to_registry: true

deploy:
  enabled: true
  service_name: "test-service"
  gcp:
    allow_unauthenticated: true
    max_instances: 10
    cpu_limit: "1000m"
    memory_limit: "512Mi"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = MultiCloudConfigLoader.load_config(f.name)

                # Test cloud config
                self.assertEqual(config.cloud.provider, "gcp")
                self.assertEqual(config.cloud.region, "us-central1")
                self.assertEqual(config.cloud.project_id, "test-project")

                # Test build config
                self.assertIsNotNone(config.build)
                self.assertEqual(config.build.entrypoint.command, "uvx")
                self.assertEqual(config.build.entrypoint.args, ["mcp-server"])
                self.assertTrue(config.build.push_to_registry)

                # Test deploy config
                self.assertIsNotNone(config.deploy)
                self.assertTrue(config.deploy.enabled)
                self.assertEqual(config.deploy.service_name, "test-service")

                gcp_config = config.deploy.get_cloud_config("gcp")
                self.assertTrue(gcp_config.allow_unauthenticated)
                self.assertEqual(gcp_config.max_instances, 10)
                self.assertEqual(gcp_config.cpu_limit, "1000m")

            finally:
                os.unlink(f.name)

    def test_load_aws_config_from_yaml(self):
        """Test loading AWS configuration from YAML."""
        yaml_content = """
cloud:
  provider: "aws"
  region: "us-west-2"

build:
  github:
    github_url: "https://github.com/example/repo"
  push_to_registry: true

deploy:
  enabled: true
  service_name: "test-service"
  aws:
    cluster_name: "test-cluster"
    vpc_id: "vpc-123456"
    alb_subnet_ids: ["subnet-1", "subnet-2"]
    ecs_subnet_ids: ["subnet-3"]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = MultiCloudConfigLoader.load_config(f.name)

                # Test cloud config
                self.assertEqual(config.cloud.provider, "aws")
                self.assertEqual(config.cloud.region, "us-west-2")

                # Test build config
                self.assertIsNotNone(config.build)
                self.assertEqual(config.build.github.github_url, "https://github.com/example/repo")
                self.assertTrue(config.build.push_to_registry)

                # Test deploy config
                self.assertIsNotNone(config.deploy)
                aws_config = config.deploy.get_cloud_config("aws")
                self.assertEqual(aws_config.cluster_name, "test-cluster")
                self.assertEqual(aws_config.vpc_id, "vpc-123456")

            finally:
                os.unlink(f.name)

    def test_backward_compatibility_mode(self):
        """Test backward compatibility with legacy config format."""
        yaml_content = """
build:
  github:
    github_url: "https://github.com/example/repo"
  push_to_ecr: true
  aws_region: "us-west-1"

deploy:
  enabled: true
  service_name: "legacy-service"
  cluster_name: "legacy-cluster"
  vpc_id: "vpc-legacy"
  alb_subnet_ids: ["subnet-1", "subnet-2"]
  ecs_subnet_ids: ["subnet-3"]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = MultiCloudConfigLoader.load_config(f.name)

                # Should default to AWS provider
                self.assertEqual(config.cloud.provider, "aws")
                self.assertEqual(config.cloud.region, "us-west-1")

                # Should handle push_to_ecr -> push_to_registry
                self.assertTrue(config.build.push_to_registry)

                # Should handle legacy AWS deploy format
                aws_config = config.deploy.get_cloud_config("aws")
                self.assertEqual(aws_config.cluster_name, "legacy-cluster")

            finally:
                os.unlink(f.name)


if __name__ == '__main__':
    unittest.main()