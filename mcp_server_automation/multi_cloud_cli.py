#!/usr/bin/env python3
"""
Multi-Cloud MCP Server Automation CLI

This CLI automates the process of transforming MCP stdio servers to Docker images
deployed on AWS ECS or Google Cloud Run using mcp-proxy.
"""

import click
from typing import Optional
from .cloud.factory import CloudProviderFactory
from .cloud_config import MultiCloudConfigLoader, MultiCloudMCPConfig
from .build import BuildCommand  # We'll update this to be cloud-agnostic
from .config import ConfigLoader  # For backward compatibility


@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.version_option()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="YAML configuration file path",
)
@click.option(
    "--provider",
    type=click.Choice(['aws', 'gcp']),
    help="Cloud provider (aws or gcp). Can be specified in config file instead.",
)
@click.option(
    "--push-to-registry",
    is_flag=True,
    help="Push the built image to container registry (ECR for AWS, Artifact Registry for GCP)",
)
@click.option(
    "--push-to-ecr",
    is_flag=True,
    help="[DEPRECATED] Use --push-to-registry instead. Push the built image to ECR (AWS only)",
)
@click.option(
    "--arch",
    type=str,
    help="Target architecture for Docker build (e.g., linux/amd64, linux/arm64)",
)
@click.option(
    "--region",
    type=str,
    help="Cloud provider region. Can be specified in config file instead.",
)
@click.option(
    "--project-id",
    type=str,
    help="GCP project ID (required for GCP). Can be specified in config file instead.",
)
@click.pass_context
def multi_cloud_cli(ctx, config, provider, push_to_registry, push_to_ecr, arch, region, project_id):
    """Build MCP server Docker image and optionally deploy to cloud platforms.

    Supports both AWS ECS and Google Cloud Run deployments.

    Usage:
      With config file: mcp-server-automation --config config.yaml
      With provider flag: mcp-server-automation --provider gcp --project-id my-project --config config.yaml
      Direct command (AWS): mcp-server-automation --provider aws --push-to-registry -- npx -y @modelcontextprotocol/server-everything
      Direct command (GCP): mcp-server-automation --provider gcp --project-id my-project --push-to-registry -- uvx mcp-server
    """

    # Get extra arguments (everything after --)
    extra_args = ctx.args

    # Handle deprecated flag
    if push_to_ecr:
        push_to_registry = True
        if not provider:
            provider = "aws"
        click.echo("⚠️  --push-to-ecr is deprecated. Use --push-to-registry instead.")

    # Ensure CLI parameters and config file work together
    if config and extra_args:
        click.echo("Error: Cannot use both --config and direct command (after --). Choose one approach.")
        return

    if not config and not extra_args:
        click.echo("Error: Either --config or direct command (after --) must be specified")
        return

    try:
        if config:
            # Config file mode - load multi-cloud configuration
            try:
                mcp_config = MultiCloudConfigLoader.load_config(config)
                detected_provider = mcp_config.provider

                # CLI provider flag overrides config file
                if provider and provider != detected_provider:
                    click.echo(f"Using CLI provider '{provider}' (overriding config file provider '{detected_provider}')")
                    # Update config with CLI provider
                    mcp_config.cloud.provider = provider
                    if project_id:
                        mcp_config.cloud.project_id = project_id
                    if region:
                        mcp_config.cloud.region = region
                else:
                    provider = detected_provider

            except Exception as e:
                # Fallback to legacy configuration for backward compatibility
                click.echo(f"⚠️  Using legacy configuration format: {str(e)}")
                return _handle_legacy_config(config, provider or "aws")

        else:
            # Direct command mode
            if not provider:
                provider = "aws"  # Default for backward compatibility
                click.echo("No provider specified, defaulting to AWS")

            if provider == "gcp" and not project_id:
                click.echo("Error: --project-id is required when using --provider gcp")
                return

            # Create configuration from CLI args
            mcp_config = _create_config_from_cli_args(
                extra_args, provider, region, project_id, push_to_registry, arch
            )

        # Validate provider dependencies
        if not CloudProviderFactory.validate_provider_dependencies(provider):
            supported_providers = CloudProviderFactory.get_supported_providers()
            click.echo(f"❌ {supported_providers[provider]} dependencies not installed.")

            if provider == "aws":
                click.echo("Install with: pip install boto3")
            elif provider == "gcp":
                click.echo("Install with: pip install google-cloud-run google-cloud-artifact-registry google-auth")
            return

        # Create cloud provider
        cloud_provider = CloudProviderFactory.create_provider(
            provider_type=provider,
            region=mcp_config.cloud.region,
            project_id=mcp_config.cloud.project_id
        )

        # Validate configuration
        if mcp_config.deploy and mcp_config.deploy.enabled:
            deploy_config_dict = {
                provider: mcp_config.deploy.get_cloud_config(provider).__dict__
            }
            cloud_provider.validate_config(deploy_config_dict)

        # Execute build using cloud provider
        _execute_multi_cloud_build(mcp_config, cloud_provider)

        # Execute deployment if enabled
        if mcp_config.deploy and mcp_config.deploy.enabled:
            _execute_multi_cloud_deployment(mcp_config, cloud_provider)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        return


def _handle_legacy_config(config_path: str, provider: str):
    """Handle legacy configuration files for backward compatibility."""
    from .cli import cli as legacy_cli

    click.echo("Using legacy AWS-only CLI...")
    # This would call the original CLI function
    # For now, we'll show an informative message
    click.echo(f"Please update your configuration file to use the new multi-cloud format.")
    click.echo(f"See config-examples/multi-cloud-{provider}.yaml for examples.")


def _create_config_from_cli_args(extra_args, provider, region, project_id, push_to_registry, arch):
    """Create multi-cloud configuration from CLI arguments."""
    from .cloud_config import (
        CloudConfig, MultiCloudBuildConfig, MultiCloudMCPConfig,
        EntrypointConfig, ContainerRegistryConfig
    )
    from .utils import Utils

    if not extra_args:
        raise ValueError("No command specified after --")

    command = extra_args[0]
    args = extra_args[1:] if len(extra_args) > 1 else []

    # Create cloud configuration
    cloud_config = CloudConfig(
        provider=provider,
        region=region or ("us-east-1" if provider == "aws" else "us-central1"),
        project_id=project_id
    )

    # Extract package name for image naming
    package_name = Utils.extract_package_name_from_args(args)

    # Create registry configuration
    registry_config = ContainerRegistryConfig(provider=provider)

    # Create entrypoint configuration
    entrypoint_config = EntrypointConfig(command=command, args=args)

    # Create build configuration
    build_config = MultiCloudBuildConfig(
        entrypoint=entrypoint_config,
        push_to_registry=push_to_registry,
        registry=registry_config,
        architecture=arch
    )

    return MultiCloudMCPConfig(
        cloud=cloud_config,
        build=build_config,
        deploy=None  # No deployment in CLI-only mode
    )


def _execute_multi_cloud_build(config: MultiCloudMCPConfig, cloud_provider):
    """Execute build process using cloud provider."""
    click.echo(f"🏗️  Building for {cloud_provider.name.upper()}...")

    # For now, this is a placeholder
    # The actual BuildCommand would need to be updated to use cloud providers
    click.echo(f"✅ Build process would execute here with {cloud_provider.name} provider")
    click.echo(f"   Provider: {cloud_provider.name}")
    click.echo(f"   Region: {cloud_provider.region}")
    if cloud_provider.project_id:
        click.echo(f"   Project: {cloud_provider.project_id}")


def _execute_multi_cloud_deployment(config: MultiCloudMCPConfig, cloud_provider):
    """Execute deployment process using cloud provider."""
    click.echo(f"🚀 Deploying to {cloud_provider.name.upper()}...")

    # For now, this is a placeholder
    # The actual deployment would use cloud_provider.deploy_container_service()
    click.echo(f"✅ Deployment process would execute here with {cloud_provider.name} provider")

    service_name = config.deploy.service_name
    click.echo(f"   Service: {service_name}")

    if cloud_provider.name == "aws":
        aws_config = config.deploy.get_cloud_config("aws")
        click.echo(f"   Cluster: {aws_config.cluster_name}")
        click.echo(f"   VPC: {aws_config.vpc_id}")
    elif cloud_provider.name == "gcp":
        gcp_config = config.deploy.get_cloud_config("gcp")
        click.echo(f"   CPU: {gcp_config.cpu_limit}")
        click.echo(f"   Memory: {gcp_config.memory_limit}")
        click.echo(f"   Max Instances: {gcp_config.max_instances}")


if __name__ == "__main__":
    multi_cloud_cli()