"""Docker operations for MCP server automation."""

import base64
import os
import shutil
import subprocess
from typing import Optional, List

import boto3
import docker


class DockerHandler:
    """Handles Docker image building and ECR operations."""

    def __init__(self):
        self.docker_client = docker.from_env()

    def generate_entrypoint_command(
        self, start_command: Optional[List[str]]
    ) -> List[str]:
        """Generate the complete ENTRYPOINT command for mcp-proxy."""
        base_command = ["mcp-proxy", "--debug", "--port", "8000", "--shell"]

        if not start_command:
            return base_command + ["python", "-m", "server"]

        # Format: mcp-proxy --debug --port 8000 --shell <command> [-- <args>]
        if len(start_command) == 1:
            return base_command + start_command
        else:
            return base_command + [start_command[0]] + ["--"] + start_command[1:]

    def build_image(
        self, build_context: str, image_tag: str, mcp_server_path: str, architecture: Optional[str] = None
    ):
        """Build Docker image using Docker Buildx."""
        if architecture:
            print(f"Building Docker image: {image_tag} for architecture: {architecture}")
        else:
            print(f"Building Docker image: {image_tag}")

        # Copy MCP server files to build context only if needed
        # (for cases where we can't install directly from repository)
        mcp_server_dest = os.path.join(build_context, "mcp-server")
        if os.path.exists(mcp_server_dest):
            shutil.rmtree(mcp_server_dest)

        # Always copy for now - the Dockerfile will decide whether to use it
        shutil.copytree(mcp_server_path, mcp_server_dest)

        # Use Docker Buildx for all builds (supports both single and multi-architecture)
        self._build_with_buildx(build_context, image_tag, architecture)

        print(f"Successfully built image: {image_tag}")

    def _build_with_buildx(self, build_context: str, image_tag: str, architecture: Optional[str] = None):
        """Build Docker image using Docker Buildx."""
        try:
            # Use docker buildx build command
            cmd = [
                "docker", "buildx", "build",
                "--tag", image_tag,
                "--load",  # Load the image into local Docker registry
            ]

            # Add platform specification if provided
            if architecture:
                cmd.extend(["--platform", architecture])

            cmd.append(build_context)

            print(f"Running buildx command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Print any output from the build process
            if result.stdout:
                print("Build output:")
                print(result.stdout)

        except subprocess.CalledProcessError as e:
            print(f"\n❌ Docker buildx build failed for image: {image_tag}")
            print("=" * 60)
            print("BUILD ERROR DETAILS:")
            print("=" * 60)

            if e.stdout:
                print("\nStdout:")
                print(e.stdout)
            if e.stderr:
                print("\nStderr:")
                print(e.stderr)

            # Check for common buildx issues
            error_message = (e.stderr or "").lower()
            if "no builder instance" in error_message or "buildx" in error_message:
                print(f"\n💡 This appears to be a Docker Buildx configuration issue.")
                if architecture:
                    print(f"   Architecture requested: {architecture}")
                print("\nTo enable multi-architecture builds, set up Docker Buildx:")
                print("   docker buildx create --name multiarch --use")
                print("   docker buildx inspect --bootstrap")
                if architecture and architecture != "linux/amd64":
                    print("   docker run --privileged --rm tonistiigi/binfmt --install all")
                print("\nMore info: https://docs.docker.com/build/building/multi-platform/")

            print("=" * 60)
            raise RuntimeError(f"Docker buildx build failed for {image_tag}. See detailed logs above.")

        except Exception as e:
            print(f"\n❌ Unexpected error during buildx build for image: {image_tag}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            raise

    def push_to_ecr(self, image_tag: str, aws_region: str):
        """Push Docker image to ECR."""
        print(f"Pushing image to ECR: {image_tag}")

        # Initialize ECR client
        ecr_client = boto3.client("ecr", region_name=aws_region)

        # Extract full repository name from image tag
        # Format: 123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-servers/mcp-src-aws-documentation-mcp-server:latest
        # We need the full repository name including the image name part
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

        # Create ECR repository if it doesn't exist
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
                    print(f"   Make sure region '{aws_region}' is valid and accessible.")

            raise

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

        # Push image - use the full image_tag directly
        # Split image_tag into repository and tag parts
        if ":" in image_tag:
            repository, tag = image_tag.rsplit(":", 1)
        else:
            repository = image_tag
            tag = "latest"

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
                    if 'id' in log:
                        status = log['status']
                        layer_id = log['id']
                        # Only show important status updates to avoid spam
                        if status in ['Pushing', 'Pushed', 'Layer already exists']:
                            if status == 'Pushed':
                                print(f"✅ {layer_id}: {status}")
                        elif 'progressDetail' in log and log['progressDetail']:
                            # Show upload progress for large layers
                            progress = log['progressDetail']
                            if 'current' in progress and 'total' in progress:
                                percent = (progress['current'] / progress['total']) * 100
                                print(f"⬆️  {layer_id}: {status} ({percent:.1f}%)")
                    else:
                        # Status without layer ID (e.g., final status)
                        print(f"📦 {log['status']}")

                # Handle errors
                elif 'error' in log:
                    error_occurred = True
                    print(f"❌ Push error: {log['error']}")

                    # Additional error details if available
                    if 'errorDetail' in log:
                        error_detail = log['errorDetail']
                        if 'message' in error_detail:
                            print(f"   Error detail: {error_detail['message']}")

            # If we collected any errors, show them and raise exception
            if error_occurred:
                print(f"\n❌ Push failed for image: {image_tag}")
                print("=" * 60)
                print("PUSH ERROR DETAILS:")
                print("=" * 60)

                for log in push_logs:
                    if 'error' in log:
                        print(f"Error: {log['error']}")
                        if 'errorDetail' in log and 'message' in log['errorDetail']:
                            print(f"Detail: {log['errorDetail']['message']}")

                print("=" * 60)
                raise Exception(f"Push failed for {image_tag}. See detailed logs above.")

        except Exception as e:
            # Handle any other push errors
            if "Push failed for" not in str(e):  # Don't double-wrap our own errors
                print(f"\n❌ Unexpected error during push for image: {image_tag}")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")

                # Common ECR authentication errors
                error_message = str(e).lower()
                if "no basic auth credentials" in error_message or "authentication required" in error_message:
                    print("\n💡 This appears to be an authentication issue.")
                    print("   Make sure you have valid AWS credentials configured.")
                    print("   Try running: aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <ecr-uri>")
                elif "repository does not exist" in error_message:
                    print("\n💡 ECR repository might not exist or you don't have access.")
                    print("   Check the repository name and your AWS permissions.")
                elif "denied" in error_message or "unauthorized" in error_message:
                    print("\n💡 Access denied - check your ECR permissions.")
                    print("   Make sure you have ECR push permissions for this repository.")

            raise

        print(f"✅ Successfully pushed image: {image_tag}")