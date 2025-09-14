"""Tests for optional dependency system."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from mcp_server_automation.cloud.factory import CloudProviderFactory


class TestOptionalDependencies(unittest.TestCase):
    """Test cases for optional dependency validation."""

    def setUp(self):
        """Set up test case."""
        # Clear any cached modules to ensure clean tests
        modules_to_clear = [
            'boto3', 'botocore',
            'google.cloud.run_v2', 'google.cloud.artifactregistry_v1', 'google.auth'
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

    def test_aws_dependencies_available(self):
        """Test AWS dependency validation when available."""
        with patch.dict('sys.modules', {'boto3': MagicMock()}):
            result = CloudProviderFactory.validate_provider_dependencies('aws')
            self.assertTrue(result)

    def test_aws_dependencies_missing(self):
        """Test AWS dependency validation when missing."""
        with patch('mcp_server_automation.cloud.factory.boto3', None):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'boto3'")):
                result = CloudProviderFactory.validate_provider_dependencies('aws')
                self.assertFalse(result)

    def test_gcp_dependencies_available(self):
        """Test GCP dependency validation when available."""
        mock_modules = {
            'google': MagicMock(),
            'google.cloud': MagicMock(),
            'google.cloud.run_v2': MagicMock(),
            'google.cloud.artifactregistry_v1': MagicMock(),
            'google.auth': MagicMock(),
        }
        with patch.dict('sys.modules', mock_modules):
            result = CloudProviderFactory.validate_provider_dependencies('gcp')
            self.assertTrue(result)

    def test_gcp_dependencies_missing(self):
        """Test GCP dependency validation when missing."""
        with patch('mcp_server_automation.cloud.factory.google', None):
            # Mock the specific import attempts in the validation function
            original_import = __builtins__['__import__']
            def mock_import(name, *args):
                if name.startswith('google.cloud'):
                    raise ImportError(f"No module named '{name}'")
                return original_import(name, *args)

            with patch('builtins.__import__', side_effect=mock_import):
                result = CloudProviderFactory.validate_provider_dependencies('gcp')
                self.assertFalse(result)

    def test_create_aws_provider_missing_dependencies(self):
        """Test creating AWS provider with missing dependencies."""
        # Mock the AWS provider import path to simulate missing dependency
        import_path = 'mcp_server_automation.cloud.aws.provider'
        with patch.dict('sys.modules', {import_path: None}):
            with patch('importlib.import_module', side_effect=ImportError("Mock AWS import failure")):
                with self.assertRaises(ImportError) as context:
                    CloudProviderFactory.create_provider(
                        provider_type='aws',
                        region='us-east-1'
                    )

                error_msg = str(context.exception)
                self.assertIn("AWS provider dependencies not installed", error_msg)
                self.assertIn("pip install 'mcp-server-automation[aws]'", error_msg)
                self.assertIn("pip install 'mcp-server-automation[all]'", error_msg)

    def test_create_gcp_provider_missing_dependencies(self):
        """Test creating GCP provider with missing dependencies."""
        # Mock the GCP provider import path to simulate missing dependency
        import_path = 'mcp_server_automation.cloud.gcp.provider'
        with patch.dict('sys.modules', {import_path: None}):
            with patch('importlib.import_module', side_effect=ImportError("Mock GCP import failure")):
                with self.assertRaises(ImportError) as context:
                    CloudProviderFactory.create_provider(
                        provider_type='gcp',
                        region='us-central1',
                        project_id='test-project'
                    )

                error_msg = str(context.exception)
                self.assertIn("GCP provider dependencies not installed", error_msg)
                self.assertIn("pip install 'mcp-server-automation[gcp]'", error_msg)
                self.assertIn("pip install 'mcp-server-automation[all]'", error_msg)

    def test_supported_providers_list(self):
        """Test getting list of supported providers."""
        providers = CloudProviderFactory.get_supported_providers()

        self.assertIn('aws', providers)
        self.assertIn('gcp', providers)
        self.assertEqual(providers['aws'], 'Amazon Web Services')
        self.assertEqual(providers['gcp'], 'Google Cloud Platform')

    def test_unknown_provider_validation(self):
        """Test validation of unknown provider."""
        result = CloudProviderFactory.validate_provider_dependencies('azure')
        self.assertFalse(result)

    def test_dependency_installation_guidance(self):
        """Test that error messages provide helpful installation guidance."""
        # Test AWS guidance
        with patch('importlib.import_module', side_effect=ImportError("Mock failure")):
            try:
                CloudProviderFactory.create_provider('aws', 'us-east-1')
            except ImportError as e:
                error_msg = str(e)
                # Check for optional dependency suggestions
                self.assertIn("[aws]", error_msg)
                self.assertIn("[all]", error_msg)
                self.assertIn("AWS Setup", error_msg)
                self.assertIn("aws configure", error_msg)

        # Test GCP guidance
        with patch('importlib.import_module', side_effect=ImportError("Mock failure")):
            try:
                CloudProviderFactory.create_provider('gcp', 'us-central1', 'test-project')
            except ImportError as e:
                error_msg = str(e)
                # Check for optional dependency suggestions
                self.assertIn("[gcp]", error_msg)
                self.assertIn("[all]", error_msg)
                self.assertIn("GCP Setup", error_msg)
                self.assertIn("gcloud auth login", error_msg)

    def test_case_insensitive_provider_names(self):
        """Test that provider names are case insensitive."""
        # Should work with uppercase
        result_upper = CloudProviderFactory.validate_provider_dependencies('AWS')
        result_lower = CloudProviderFactory.validate_provider_dependencies('aws')
        result_mixed = CloudProviderFactory.validate_provider_dependencies('AwS')

        # All should return the same result (whether deps are available or not)
        self.assertEqual(result_upper, result_lower)
        self.assertEqual(result_lower, result_mixed)


if __name__ == '__main__':
    unittest.main()