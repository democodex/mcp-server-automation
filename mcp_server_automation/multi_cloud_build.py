"""Multi-cloud build system for MCP server automation."""

import os
import tempfile
from typing import Optional, List
from .cloud.base import CloudProvider
from .cloud_config import MultiCloudBuildConfig
from .github_handler import GitHubHandler
from .package_detector import PackageDetector
from .dockerfile_generator import DockerfileGenerator
from .docker_handler import DockerHandler
from .utils import Utils


class MultiCloudBuildCommand:
    """Handles building and pushing MCP server Docker images for multiple cloud providers."""

    def __init__(self):
        self.github_handler = GitHubHandler()
        self.package_detector = PackageDetector()
        self.dockerfile_generator = DockerfileGenerator()
        self.docker_handler = DockerHandler()

    def execute(
        self,
        build_config: MultiCloudBuildConfig,
        cloud_provider: CloudProvider,
    ) -> str:
        """Execute the multi-cloud build process.

        Args:
            build_config: Build configuration
            cloud_provider: Cloud provider instance

        Returns:
            Image URI for the built and pushed image
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"🏗️  Building MCP server for {cloud_provider.name.upper()}...")

            # Step 1: Determine build mode and prepare source
            if build_config.entrypoint:
                # Entrypoint mode - create minimal directory structure
                mcp_server_path = temp_dir
                print(f"Building entrypoint command: {build_config.entrypoint.command} {' '.join(build_config.entrypoint.args or [])}")
            else:
                # GitHub mode - fetch repository
                if not build_config.github:
                    raise ValueError("Either entrypoint or github configuration must be specified")
                mcp_server_path = self.github_handler.fetch_repository(
                    build_config.github.github_url,
                    build_config.github.subfolder,
                    temp_dir,
                    build_config.github.branch
                )

            # Step 2: Detect package information (adapted for multi-cloud)
            package_info = self._detect_package_info(
                mcp_server_path,
                build_config,
                cloud_provider
            )

            # Step 3: Generate Dockerfile
            dockerfile_content = self.dockerfile_generator.generate_dockerfile(
                package_info, build_config.dockerfile_path
            )
            dockerfile_full_path = os.path.join(temp_dir, "Dockerfile")
            with open(dockerfile_full_path, "w", encoding='utf-8') as f:
                f.write(dockerfile_content)

            # Step 4: Build Docker image locally
            image_name = self._generate_image_name(build_config, cloud_provider)
            local_tag = self._generate_local_tag(build_config, cloud_provider)

            self.docker_handler.build_image(
                temp_dir, local_tag, mcp_server_path, build_config.architecture
            )

            # Step 5: Push to cloud registry (if enabled)
            if build_config.push_to_registry:
                registry_url = cloud_provider.registry_ops.build_registry_url()
                registry_tag = self._generate_registry_tag(
                    registry_url, image_name, build_config, cloud_provider
                )

                print(f"📦 Pushing to {cloud_provider.name.upper()} registry: {registry_tag}")

                registry_result = cloud_provider.registry_ops.push_image(
                    registry_tag, local_tag
                )

                print(f"✅ Successfully pushed image: {registry_result.image_uri}")
                return registry_result.image_uri
            else:
                print(f"Skipping registry push. Image built locally as: {local_tag}")
                return local_tag

    def _detect_package_info(
        self,
        mcp_server_path: str,
        build_config: MultiCloudBuildConfig,
        cloud_provider: CloudProvider
    ) -> dict:
        """Detect package information adapted for multi-cloud builds."""
        if build_config.entrypoint:
            # Entrypoint mode
            return self.package_detector.detect_package_info(
                mcp_server_path,
                build_config.command_override,
                build_config.environment_variables,
                github_url=None,
                subfolder=None,
                branch=None,
                entrypoint_command=build_config.entrypoint.command,
                entrypoint_args=build_config.entrypoint.args,
            )
        else:
            # GitHub mode
            return self.package_detector.detect_package_info(
                mcp_server_path,
                build_config.command_override,
                build_config.environment_variables,
                github_url=build_config.github.github_url,
                subfolder=build_config.github.subfolder,
                branch=build_config.github.branch,
                entrypoint_command=None,
                entrypoint_args=None,
            )

    def _generate_image_name(
        self,
        build_config: MultiCloudBuildConfig,
        cloud_provider: CloudProvider
    ) -> str:
        """Generate image name based on build configuration."""
        if build_config.image and build_config.image.repository:
            # Use custom image name if provided
            return build_config.image.repository.split("/")[-1]

        # Auto-generate image name
        if build_config.entrypoint:
            # For entrypoint mode, use command and args
            package_name = Utils.extract_package_name_from_args(build_config.entrypoint.args or [])
            if package_name:
                clean_name = Utils.clean_package_name(package_name)
                return f"mcp-{clean_name}"
            else:
                return f"mcp-{build_config.entrypoint.command}"
        else:
            # For GitHub mode, use repository name
            repo_name = build_config.github.github_url.rstrip(".git").split("/")[-1]
            if build_config.github.subfolder:
                subfolder_name = build_config.github.subfolder.strip("/").replace("/", "-")
                return f"{repo_name}-{subfolder_name}"
            return repo_name

    def _generate_local_tag(
        self,
        build_config: MultiCloudBuildConfig,
        cloud_provider: CloudProvider
    ) -> str:
        """Generate local Docker tag."""
        image_name = self._generate_image_name(build_config, cloud_provider)
        timestamp_tag = Utils.generate_static_tag()
        return f"mcp-local/{image_name}:{timestamp_tag}"

    def _generate_registry_tag(
        self,
        registry_url: str,
        image_name: str,
        build_config: MultiCloudBuildConfig,
        cloud_provider: CloudProvider
    ) -> str:
        """Generate registry tag for pushing."""
        if build_config.image and build_config.image.tag:
            tag = build_config.image.tag
        else:
            # Generate dynamic tag
            if build_config.entrypoint:
                tag = Utils.generate_static_tag()
            else:
                # For GitHub mode, use commit hash + timestamp
                from .config import ConfigLoader
                tag = ConfigLoader._generate_dynamic_tag(
                    build_config.github.github_url,
                    build_config.github.branch
                )

        # Build full registry tag based on provider
        if cloud_provider.name == "aws":
            # AWS ECR format: account.dkr.ecr.region.amazonaws.com/repository:tag
            repository_name = build_config.registry.repository_name
            return f"{registry_url}/{repository_name}/{image_name}:{tag}"
        elif cloud_provider.name == "gcp":
            # GCP Artifact Registry format: region-docker.pkg.dev/project/repository/image:tag
            repository_name = build_config.registry.repository_name
            return f"{registry_url}/{repository_name}/{image_name}:{tag}"
        else:
            raise ValueError(f"Unsupported provider: {cloud_provider.name}")

    def get_image_uri_for_deployment(
        self,
        build_config: MultiCloudBuildConfig,
        cloud_provider: CloudProvider
    ) -> str:
        """Get the image URI that should be used for deployment."""
        if build_config.image and build_config.image.repository:
            # Use explicitly configured image
            tag = build_config.image.tag or "latest"
            return f"{build_config.image.repository}:{tag}"

        if not build_config.push_to_registry:
            raise ValueError("Cannot deploy without pushing to registry. Set push_to_registry: true")

        # Generate the same tag that would be used during build/push
        registry_url = cloud_provider.registry_ops.build_registry_url()
        image_name = self._generate_image_name(build_config, cloud_provider)
        return self._generate_registry_tag(registry_url, image_name, build_config, cloud_provider)