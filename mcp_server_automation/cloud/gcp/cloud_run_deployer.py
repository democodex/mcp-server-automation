"""Google Cloud Run deployment operations."""

import subprocess
import json
import time
from typing import Optional
from ..base import DeploymentOperations, DeploymentResult


class CloudRunDeployer(DeploymentOperations):
    """Handles Google Cloud Run deployment for MCP server automation."""

    def __init__(self, region: str, project_id: str):
        self.region = region
        self.project_id = project_id

    def deploy_service(self, config) -> DeploymentResult:
        """Deploy service to Google Cloud Run."""
        from ...cloud_config import MultiCloudDeployConfig

        # Extract GCP-specific configuration
        gcp_config = config.get_cloud_config('gcp')

        service_name = config.service_name
        image_uri = getattr(config, 'image_uri', None)
        port = config.port

        if not image_uri:
            raise ValueError("Image URI is required for Cloud Run deployment")

        try:
            print(f"Deploying service '{service_name}' to Cloud Run...")

            # Build gcloud command
            cmd = [
                "gcloud", "run", "deploy", service_name,
                "--image", image_uri,
                "--region", self.region,
                "--project", self.project_id,
                "--port", str(port),
                "--platform", "managed",
                "--format", "json"
            ]

            # Add GCP-specific configuration
            if gcp_config.allow_unauthenticated:
                cmd.extend(["--allow-unauthenticated"])

            # Resource limits
            cmd.extend([
                "--cpu", gcp_config.cpu_limit,
                "--memory", gcp_config.memory_limit,
                "--max-instances", str(gcp_config.max_instances)
            ])

            # Ingress settings
            cmd.extend(["--ingress", gcp_config.ingress])

            # Environment variables (if any)
            env_vars = getattr(config, 'environment_variables', None)
            if env_vars:
                for key, value in env_vars.items():
                    cmd.extend(["--set-env-vars", f"{key}={value}"])

            print(f"Running: {' '.join(cmd[:8])} ...")  # Don't print full command for security

            # Deploy the service
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Parse deployment result
            deployment_info = json.loads(result.stdout) if result.stdout else {}
            service_url = deployment_info.get('status', {}).get('url', '')

            if not service_url:
                # Fallback to get service URL
                service_url = self.get_service_url(service_name)

            print(f"✅ Successfully deployed Cloud Run service: {service_name}")
            print(f"   Service URL: {service_url}")

            return DeploymentResult(
                service_url=service_url,
                service_name=service_name,
                deployment_info={
                    "region": self.region,
                    "project_id": self.project_id,
                    "platform": "Cloud Run",
                    "image": image_uri,
                    **deployment_info
                }
            )

        except subprocess.CalledProcessError as e:
            print(f"❌ Cloud Run deployment failed: {e.stderr}")

            error_message = e.stderr.lower()
            if "permission denied" in error_message or "forbidden" in error_message:
                print("\n💡 Permission denied - check your Cloud Run permissions:")
                print("   Make sure you have the 'Cloud Run Admin' role")
                print("   Or these specific permissions:")
                print("   - run.services.create")
                print("   - run.services.update")
                print("   - run.services.setIamPolicy (if setting public access)")
            elif "image" in error_message and "not found" in error_message:
                print("\n💡 Container image not found:")
                print("   Make sure the image was successfully pushed to Artifact Registry")
                print("   Check the image URI format and permissions")
            elif "quota" in error_message or "limit" in error_message:
                print("\n💡 Resource quota exceeded:")
                print("   Check your Cloud Run quotas and limits")
                print("   Consider reducing resource requirements or requesting quota increase")
            elif "project" in error_message:
                print(f"\n💡 Project issue:")
                print(f"   Make sure project '{self.project_id}' exists and is accessible")
                print("   Verify billing is enabled for the project")

            raise Exception(f"Cloud Run deployment failed: {e.stderr}")

    def get_service_url(self, service_name: str) -> str:
        """Get Cloud Run service URL."""
        try:
            result = subprocess.run([
                "gcloud", "run", "services", "describe", service_name,
                "--region", self.region,
                "--project", self.project_id,
                "--format", "value(status.url)"
            ], capture_output=True, text=True, check=True)

            service_url = result.stdout.strip()
            if not service_url:
                raise RuntimeError(f"Could not retrieve URL for service: {service_name}")

            return service_url

        except subprocess.CalledProcessError as e:
            if "not found" in e.stderr.lower():
                raise RuntimeError(f"Cloud Run service '{service_name}' not found")
            raise Exception(f"Failed to get service URL: {e.stderr}")

    def delete_service(self, service_name: str) -> None:
        """Delete Cloud Run service."""
        try:
            print(f"Deleting Cloud Run service '{service_name}'...")

            result = subprocess.run([
                "gcloud", "run", "services", "delete", service_name,
                "--region", self.region,
                "--project", self.project_id,
                "--quiet"  # Skip confirmation prompt
            ], capture_output=True, text=True, check=True)

            print(f"✅ Successfully deleted Cloud Run service: {service_name}")

        except subprocess.CalledProcessError as e:
            if "not found" in e.stderr.lower():
                print(f"Cloud Run service '{service_name}' does not exist, nothing to delete")
            else:
                print(f"❌ Failed to delete Cloud Run service: {e.stderr}")
                raise Exception(f"Service deletion failed: {e.stderr}")

    def setup_custom_domain(self, service_name: str, domain: str) -> None:
        """Set up custom domain for Cloud Run service."""
        try:
            print(f"Setting up custom domain '{domain}' for service '{service_name}'...")

            # Create domain mapping
            result = subprocess.run([
                "gcloud", "run", "domain-mappings", "create",
                "--service", service_name,
                "--domain", domain,
                "--region", self.region,
                "--project", self.project_id
            ], capture_output=True, text=True, check=True)

            print(f"✅ Custom domain mapping created successfully")
            print("🔧 Complete the domain setup by:")
            print("   1. Adding the provided DNS records to your domain")
            print("   2. Waiting for DNS propagation (can take up to 24 hours)")
            print("   3. SSL certificate will be automatically provisioned")

        except subprocess.CalledProcessError as e:
            print(f"❌ Custom domain setup failed: {e.stderr}")

            error_message = e.stderr.lower()
            if "already exists" in error_message:
                print("💡 Domain mapping already exists")
            elif "verification" in error_message:
                print("\n💡 Domain verification required:")
                print("   You need to verify domain ownership first")
                print("   Follow the verification instructions in Google Cloud Console")
            elif "permission" in error_message:
                print("\n💡 Permission denied:")
                print("   Make sure you have domain mapping permissions")

            raise Exception(f"Custom domain setup failed: {e.stderr}")

    def get_service_logs(self, service_name: str, limit: int = 100) -> None:
        """Get recent logs for the Cloud Run service."""
        try:
            print(f"Fetching logs for Cloud Run service '{service_name}'...")

            result = subprocess.run([
                "gcloud", "logging", "read",
                f'resource.type="cloud_run_revision" resource.labels.service_name="{service_name}"',
                "--project", self.project_id,
                "--limit", str(limit),
                "--format", "table(timestamp,severity,textPayload)"
            ], capture_output=True, text=True, check=True)

            if result.stdout.strip():
                print("Recent logs:")
                print(result.stdout)
            else:
                print("No recent logs found")

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to fetch logs: {e.stderr}")
            print("💡 You can view logs in Google Cloud Console:")
            print(f"   https://console.cloud.google.com/run/detail/{self.region}/{service_name}/logs?project={self.project_id}")

    def check_service_health(self, service_name: str) -> bool:
        """Check if the Cloud Run service is healthy."""
        try:
            service_url = self.get_service_url(service_name)

            # Make a health check request to the MCP endpoint
            import requests
            health_url = f"{service_url}/mcp"

            print(f"Performing health check: {health_url}")
            response = requests.get(health_url, timeout=30)

            # For MCP servers, we expect HTTP 400 (Bad Request) as a healthy response
            # because /mcp endpoint expects proper MCP protocol messages
            if response.status_code == 400:
                print("✅ Service health check passed (HTTP 400 - MCP endpoint responding)")
                return True
            else:
                print(f"⚠️ Unexpected health check response: HTTP {response.status_code}")
                print("   This might indicate the service is not properly configured")
                return False

        except requests.RequestException as e:
            print(f"❌ Health check failed: {str(e)}")
            print("💡 Common issues:")
            print("   - Service is still starting up (wait a few minutes)")
            print("   - Network connectivity issues")
            print("   - Service is not responding on the expected port")
            return False
        except Exception as e:
            print(f"❌ Health check error: {str(e)}")
            return False