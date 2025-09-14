"""Tests for cloud provider factory."""

import unittest
from unittest.mock import patch, MagicMock
from mcp_server_automation.cloud.factory import CloudProviderFactory


class TestCloudProviderFactory(unittest.TestCase):
    """Test cases for CloudProviderFactory."""

    def test_get_supported_providers(self):
        """Test getting supported providers list."""
        providers = CloudProviderFactory.get_supported_providers()
        self.assertIn('aws', providers)
        self.assertIn('gcp', providers)
        self.assertEqual(providers['aws'], 'Amazon Web Services')
        self.assertEqual(providers['gcp'], 'Google Cloud Platform')

    @patch('mcp_server_automation.cloud.factory.boto3')
    def test_validate_aws_dependencies_available(self, mock_boto3):
        """Test AWS dependency validation when available."""
        result = CloudProviderFactory.validate_provider_dependencies('aws')
        self.assertTrue(result)

    @patch('mcp_server_automation.cloud.factory.boto3', side_effect=ImportError())
    def test_validate_aws_dependencies_missing(self, mock_boto3):
        """Test AWS dependency validation when missing."""
        result = CloudProviderFactory.validate_provider_dependencies('aws')
        self.assertFalse(result)

    def test_validate_gcp_dependencies_missing(self):
        """Test GCP dependency validation when missing."""
        with patch('mcp_server_automation.cloud.factory.google.cloud.run_v2', side_effect=ImportError()):
            result = CloudProviderFactory.validate_provider_dependencies('gcp')
            self.assertFalse(result)

    def test_validate_unknown_provider(self):
        """Test validation of unknown provider."""
        result = CloudProviderFactory.validate_provider_dependencies('unknown')
        self.assertFalse(result)

    @patch('mcp_server_automation.cloud.aws.provider.AWSProvider')
    def test_create_aws_provider(self, mock_aws_provider):
        """Test creating AWS provider."""
        mock_provider = MagicMock()
        mock_aws_provider.return_value = mock_provider

        provider = CloudProviderFactory.create_provider(
            provider_type='aws',
            region='us-east-1',
            project_id='123456789012'
        )

        mock_aws_provider.assert_called_once_with(
            region='us-east-1', account_id='123456789012'
        )
        self.assertEqual(provider, mock_provider)

    def test_create_gcp_provider_without_project_id(self):
        """Test creating GCP provider without project ID raises error."""
        with self.assertRaises(ValueError) as context:
            CloudProviderFactory.create_provider(
                provider_type='gcp',
                region='us-central1'
            )
        self.assertIn("project_id is required for GCP provider", str(context.exception))

    @patch('mcp_server_automation.cloud.gcp.provider.GCPProvider')
    def test_create_gcp_provider(self, mock_gcp_provider):
        """Test creating GCP provider."""
        mock_provider = MagicMock()
        mock_gcp_provider.return_value = mock_provider

        provider = CloudProviderFactory.create_provider(
            provider_type='gcp',
            region='us-central1',
            project_id='my-project'
        )

        mock_gcp_provider.assert_called_once_with(
            region='us-central1', project_id='my-project'
        )
        self.assertEqual(provider, mock_provider)

    def test_create_unsupported_provider(self):
        """Test creating unsupported provider raises error."""
        with self.assertRaises(ValueError) as context:
            CloudProviderFactory.create_provider(
                provider_type='azure',
                region='eastus'
            )
        self.assertIn("Unsupported provider type: azure", str(context.exception))

    @patch('mcp_server_automation.cloud.factory.boto3', side_effect=ImportError())
    def test_create_aws_provider_missing_dependencies(self, mock_boto3):
        """Test creating AWS provider with missing dependencies."""
        with self.assertRaises(ImportError) as context:
            CloudProviderFactory.create_provider(
                provider_type='aws',
                region='us-east-1'
            )
        self.assertIn("AWS provider dependencies not installed", str(context.exception))


if __name__ == '__main__':
    unittest.main()