"""AWS ECR (Elastic Container Registry) operations."""

import base64
from typing import Optional
import boto3
import docker
from ..base import ContainerRegistryOperations, RegistryResult


class ECRHandler(ContainerRegistryOperations):
    """Handles AWS ECR operations for MCP server automation."""

    def __init__(self, region: str, account_id: Optional[str] = None):
        self.region = region
        self.account_id = account_id
        self.docker_client = docker.from_env()
        self.ecr_client = None

    def _get_ecr_client(self):
        """Get or create ECR client."""
        if not self.ecr_client:
            self.ecr_client = boto3.client("ecr", region_name=self.region)
        return self.ecr_client

    def build_registry_url(self, project_id: Optional[str] = None) -> str:
        """Build ECR registry URL using AWS account ID."""
        if not self.account_id:
            # Get account ID from STS
            sts_client = boto3.client("sts", region_name=self.region)
            self.account_id = sts_client.get_caller_identity()["Account"]

        return f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com"

    def authenticate(self) -> None:
        """Authenticate Docker client with ECR."""
        ecr_client = self._get_ecr_client()

        # Get ECR login token
        token_response = ecr_client.get_authorization_token()
        token = token_response["authorizationData"][0]["authorizationToken"]
        endpoint = token_response["authorizationData"][0]["proxyEndpoint"]

        # Decode token
        username, password = base64.b64decode(token).decode().split(":")

        # Login to ECR
        self.docker_client.login(
            username=username, password=password, registry=endpoint
        )
        print(f"✅ Successfully authenticated with ECR in region {self.region}")

    def create_repository_if_needed(self, repo_name: str) -> None:
        """Create ECR repository if it doesn't exist."""
        ecr_client = self._get_ecr_client()

        try:
            ecr_client.describe_repositories(repositoryNames=[repo_name])
            print(f"ECR repository '{repo_name}' already exists")
        except ecr_client.exceptions.RepositoryNotFoundException:
            try:
                print(f"Creating ECR repository '{repo_name}'...")
                ecr_client.create_repository(
                    repositoryName=repo_name,
                    imageScanningConfiguration={"scanOnPush": True},
                    encryptionConfiguration={"encryptionType": "AES256"},
                )
                print(f"✅ ECR repository '{repo_name}' created successfully")
            except Exception as e:
                print(f"\n❌ Failed to create ECR repository '{repo_name}'")
                print(f"Error: {str(e)}")

                # Common ECR creation errors
                error_message = str(e).lower()
                if "access denied" in error_message or "unauthorized" in error_message:
                    print("\n💡 Access denied - check your ECR permissions.")
                    print("   Make sure you have 'ecr:CreateRepository' permission.")
                elif "limit exceeded" in error_message:
                    print("\n💡 ECR repository limit exceeded.")
                    print("   Delete unused repositories or request a limit increase.")

                raise Exception(f"ECR repository creation failed: {str(e)}")
        except Exception as e:
            if "ECR repository creation failed" not in str(e):
                print(f"\n❌ Error checking/creating ECR repository '{repo_name}'")
                print(f"Error: {str(e)}")

                # Handle AWS credential/permission errors
                error_message = str(e).lower()
                if "credentials" in error_message or "unable to locate credentials" in error_message:
                    print("\n💡 AWS credentials issue.")
                    print("   Make sure you have valid AWS credentials configured.")
                    print("   Try: aws configure or set AWS_PROFILE environment variable.")
                elif "region" in error_message:
                    print(f"\n💡 AWS region issue.")
                    print(f"   Make sure region '{self.region}' is valid and accessible.")

            raise

    def push_image(self, image_tag: str, local_tag: str) -> RegistryResult:
        """Push Docker image to ECR."""
        print(f"Pushing image to ECR: {image_tag}")

        # Extract repository name from image tag
        repo_name = self._extract_repository_name(image_tag)

        # Create repository if needed
        self.create_repository_if_needed(repo_name)

        # Authenticate with ECR
        self.authenticate()

        # Split image_tag into repository and tag parts
        if ":" in image_tag:
            repository, tag = image_tag.rsplit(":", 1)
        else:
            repository = image_tag
            tag = "latest"

        # Tag the local image with the ECR repository
        self.docker_client.images.get(local_tag).tag(repository, tag)

        # Push the image with enhanced error handling
        try:
            push_logs = []
            error_occurred = False

            for log in self.docker_client.images.push(
                repository=repository, tag=tag, stream=True, decode=True
            ):
                push_logs.append(log)

                # Print progress for key status updates
                if 'status' in log:
                    status = log['status']
                    if 'Pushed' in status or 'Layer already exists' in status:
                        if 'id' in log:
                            print(f"  {status}: {log['id']}")
                    elif 'Pushing' in status and 'progressDetail' in log:
                        if log['progressDetail']:
                            # Show progress for large layers
                            progress = log['progressDetail']
                            if 'current' in progress and 'total' in progress:
                                percent = int((progress['current'] / progress['total']) * 100)
                                print(f"  {status} {log.get('id', '')}: {percent}%")

                # Check for errors
                if 'error' in log:
                    error_occurred = True
                    error_message = log['error']
                    print(f"\n❌ Push failed: {error_message}")

                    # Provide specific error guidance
                    if "denied" in error_message.lower():
                        print("\n💡 Push denied - this usually means:")
                        print("   1. Repository doesn't exist or you don't have access")
                        print("   2. ECR authentication expired")
                        print("   3. Wrong repository name or region")
                    elif "no basic auth credentials" in error_message.lower():
                        print("\n💡 Authentication issue.")
                        print("   Make sure you have valid AWS credentials configured.")
                        print("   Try running: aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <ecr-uri>")
                    elif "repository does not exist" in error_message.lower():
                        print("\n💡 ECR repository might not exist or you don't have access.")
                        print("   Check the repository name and your AWS permissions.")
                    elif "access denied" in error_message.lower():
                        print("\n💡 Access denied - check your ECR permissions.")
                        print("   Make sure you have ECR push permissions for this repository.")

            if error_occurred:
                raise Exception("Image push failed - see error messages above")

            print(f"✅ Successfully pushed image: {image_tag}")

            registry_url = self.build_registry_url()
            return RegistryResult(
                image_uri=image_tag,
                registry_url=registry_url,
                repository_name=repo_name
            )

        except Exception as e:
            if "Image push failed" not in str(e):
                print(f"\n❌ Unexpected error during push: {str(e)}")

                # Common ECR push errors
                error_message = str(e).lower()
                if "connection" in error_message:
                    print("\n💡 Connection issue.")
                    print("   Check your internet connection and AWS region accessibility.")
                elif "timeout" in error_message:
                    print("\n💡 Timeout occurred.")
                    print("   The image might be large. Try again or check your connection.")

            raise

    def _extract_repository_name(self, image_tag: str) -> str:
        """Extract repository name from image tag."""
        # Format: 123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-servers/image-name:tag
        if ":" in image_tag:
            image_without_tag = image_tag.rsplit(":", 1)[0]
        else:
            image_without_tag = image_tag

        # Extract everything after the registry URL as the repository name
        registry_parts = image_without_tag.split("/")
        if len(registry_parts) >= 2:
            # Join everything after the registry URL (account.dkr.ecr.region.amazonaws.com)
            repo_name = "/".join(registry_parts[1:])
        else:
            repo_name = registry_parts[-1]

        return repo_name