"""Google Cloud Artifact Registry operations."""

import subprocess
from typing import Optional
from ..base import ContainerRegistryOperations, RegistryResult


class ArtifactRegistryHandler(ContainerRegistryOperations):
    """Handles Google Cloud Artifact Registry operations for MCP server automation."""

    def __init__(self, region: str, project_id: str):
        self.region = region
        self.project_id = project_id
        self.repository_name = "mcp-servers"  # Default repository name

    def build_registry_url(self, project_id: Optional[str] = None) -> str:
        """Build Artifact Registry URL."""
        pid = project_id or self.project_id
        return f"{self.region}-docker.pkg.dev/{pid}"

    def authenticate(self) -> None:
        """Authenticate Docker client with Artifact Registry."""
        try:
            print(f"Authenticating Docker with Google Cloud Artifact Registry...")

            # Configure Docker to use gcloud as credential helper
            result = subprocess.run([
                "gcloud", "auth", "configure-docker",
                f"{self.region}-docker.pkg.dev"
            ], capture_output=True, text=True, check=True)

            print("✅ Successfully authenticated with Artifact Registry")

        except subprocess.CalledProcessError as e:
            print(f"❌ Authentication failed: {e.stderr}")
            print("\n💡 Authentication troubleshooting:")
            print("   1. Make sure Google Cloud CLI is installed: https://cloud.google.com/sdk/docs/install")
            print("   2. Authenticate with gcloud: gcloud auth login")
            print("   3. Set default project: gcloud config set project PROJECT_ID")
            print("   4. Make sure you have Artifact Registry permissions")
            raise Exception(f"Artifact Registry authentication failed: {e.stderr}")
        except FileNotFoundError:
            print("❌ Google Cloud CLI (gcloud) not found")
            print("\n💡 Please install Google Cloud CLI:")
            print("   https://cloud.google.com/sdk/docs/install")
            raise Exception("Google Cloud CLI is required for authentication")

    def create_repository_if_needed(self, repo_name: str) -> None:
        """Create Artifact Registry repository if it doesn't exist."""
        try:
            print(f"Checking if Artifact Registry repository '{repo_name}' exists...")

            # Check if repository exists
            check_result = subprocess.run([
                "gcloud", "artifacts", "repositories", "describe", repo_name,
                "--location", self.region,
                "--project", self.project_id,
                "--format", "value(name)"
            ], capture_output=True, text=True)

            if check_result.returncode == 0 and check_result.stdout.strip():
                print(f"Artifact Registry repository '{repo_name}' already exists")
                return

            print(f"Creating Artifact Registry repository '{repo_name}'...")

            # Create repository
            create_result = subprocess.run([
                "gcloud", "artifacts", "repositories", "create", repo_name,
                "--repository-format", "docker",
                "--location", self.region,
                "--project", self.project_id,
                "--description", f"MCP server container repository"
            ], capture_output=True, text=True, check=True)

            print(f"✅ Artifact Registry repository '{repo_name}' created successfully")

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create Artifact Registry repository '{repo_name}'")
            print(f"Error: {e.stderr}")

            error_message = e.stderr.lower()
            if "permission denied" in error_message or "forbidden" in error_message:
                print("\n💡 Permission denied - check your Artifact Registry permissions:")
                print("   Make sure you have the 'Artifact Registry Admin' role")
                print("   Or these specific permissions:")
                print("   - artifactregistry.repositories.create")
                print("   - artifactregistry.repositories.get")
            elif "already exists" in error_message:
                print("\n💡 Repository might already exist with different settings")
            elif "project" in error_message:
                print(f"\n💡 Project issue - make sure project '{self.project_id}' exists and is accessible")
            elif "location" in error_message:
                print(f"\n💡 Location issue - make sure region '{self.region}' supports Artifact Registry")

            raise Exception(f"Artifact Registry repository creation failed: {e.stderr}")

    def push_image(self, image_tag: str, local_tag: str) -> RegistryResult:
        """Push Docker image to Artifact Registry."""
        print(f"Pushing image to Artifact Registry: {image_tag}")

        try:
            # Ensure repository exists
            repo_name = self._extract_repository_name(image_tag)
            self.create_repository_if_needed(repo_name)

            # Authenticate with Artifact Registry
            self.authenticate()

            # Tag the local image with the Artifact Registry URL
            print(f"Tagging local image {local_tag} as {image_tag}")
            tag_result = subprocess.run([
                "docker", "tag", local_tag, image_tag
            ], capture_output=True, text=True, check=True)

            # Push the image
            print(f"Pushing {image_tag} to Artifact Registry...")
            push_result = subprocess.run([
                "docker", "push", image_tag
            ], capture_output=True, text=True, check=True)

            # Show push output
            if push_result.stdout:
                print("Push output:")
                print(push_result.stdout)

            print(f"✅ Successfully pushed image: {image_tag}")

            registry_url = self.build_registry_url()
            return RegistryResult(
                image_uri=image_tag,
                registry_url=registry_url,
                repository_name=repo_name
            )

        except subprocess.CalledProcessError as e:
            print(f"❌ Image push failed: {e.stderr}")

            error_message = e.stderr.lower()
            if "permission denied" in error_message or "forbidden" in error_message:
                print("\n💡 Push permission denied:")
                print("   Make sure you have 'Artifact Registry Writer' role")
                print("   Or artifactregistry.repositories.uploadArtifacts permission")
            elif "not found" in error_message:
                print("\n💡 Repository or image not found:")
                print("   Check the repository name and region")
                print("   Make sure the local image exists")
            elif "authentication required" in error_message:
                print("\n💡 Authentication issue:")
                print("   Try running: gcloud auth configure-docker")
            elif "connection" in error_message:
                print("\n💡 Connection issue:")
                print("   Check internet connectivity and Google Cloud service status")

            raise Exception(f"Image push failed: {e.stderr}")

    def _extract_repository_name(self, image_tag: str) -> str:
        """Extract repository name from image tag."""
        # Format: us-central1-docker.pkg.dev/project-id/repo-name/image-name:tag
        if ":" in image_tag:
            image_without_tag = image_tag.rsplit(":", 1)[0]
        else:
            image_without_tag = image_tag

        # Split by / and get the repository name (3rd from end)
        # Example: us-central1-docker.pkg.dev/my-project/mcp-servers/my-image
        # Parts: [region-docker.pkg.dev, project-id, repo-name, image-name]
        parts = image_without_tag.split("/")
        if len(parts) >= 3:
            return parts[-2]  # repo-name
        else:
            return self.repository_name  # fallback to default