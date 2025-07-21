#!/usr/bin/env python3
"""
MCP Server Automation CLI

This CLI automates the process of transforming MCP stdio servers to Docker images
deployed on AWS ECS using mcp-proxy.
"""

import click
from .build import BuildCommand
from .deploy import DeployCommand
from .config import ConfigLoader


@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.version_option()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="YAML configuration file path",
)
@click.option(
    "--push-to-ecr",
    is_flag=True,
    help="Push the built image to ECR",
)
@click.option(
    "--arch",
    type=str,
    help="Target architecture for Docker build (e.g., linux/amd64, linux/arm64)",
)
@click.pass_context
def cli(ctx, config, push_to_ecr, arch):
    """Build MCP server Docker image and optionally deploy to ECS.
    
    Usage:
      With config file: mcp-server-automation --config config.yaml
      With direct command: mcp-server-automation --push-to-ecr -- npx -y @modelcontextprotocol/server-everything
      With architecture: mcp-server-automation --arch linux/arm64 -- npx -y @modelcontextprotocol/server-everything
    """
    
    # Get extra arguments (everything after --)
    extra_args = ctx.args
    
    # Ensure CLI parameters and config file are mutually exclusive
    if config and extra_args:
        click.echo("Error: Cannot use both --config and direct command (after --). Choose one approach.")
        return
    
    if config and arch:
        click.echo("Error: Cannot use --arch with --config. Specify architecture in the config file instead.")
        return
    
    if not config and not extra_args:
        click.echo("Error: Either --config or direct command (after --) must be specified")
        return
    
    if config:
        # Config file mode
        mcp_config = ConfigLoader.load_config(config)
        if not mcp_config.build:
            click.echo("Error: No 'build' section found in configuration file")
            return
    else:
        # CLI-only entrypoint mode with -- separator
        if not extra_args:
            click.echo("Error: No command specified after --")
            return
            
        command = extra_args[0]
        args = extra_args[1:] if len(extra_args) > 1 else []
        
        from types import SimpleNamespace
        mcp_config = SimpleNamespace()
        mcp_config.build = SimpleNamespace()
        mcp_config.deploy = None
        
        # Create entrypoint configuration from CLI args
        mcp_config.build.entrypoint = SimpleNamespace()
        mcp_config.build.entrypoint.command = command
        mcp_config.build.entrypoint.args = args
        
        # Extract package name for image naming
        from .utils import Utils
        package_name = Utils.extract_package_name_from_args(args)
        
        # Set required defaults for CLI-only mode
        mcp_config.build.push_to_ecr = push_to_ecr
        if package_name:
            # Clean package name for Docker image naming
            clean_name = Utils.clean_package_name(package_name)
            mcp_config.build.image_name = f"mcp-{clean_name}"
        else:
            mcp_config.build.image_name = f"mcp-{command}"
        mcp_config.build.ecr_repository = None
        mcp_config.build.aws_region = None
        mcp_config.build.dockerfile_path = None
        mcp_config.build.command_override = None
        mcp_config.build.environment_variables = None
        mcp_config.build.architecture = arch  # Add architecture from CLI parameter

    build_config = mcp_config.build
    deploy_config = mcp_config.deploy

    # Validate deployment requirements
    if deploy_config and deploy_config.enabled:
        if not build_config.push_to_ecr:
            click.echo("Error: deploy.enabled requires build.push_to_ecr to be true")
            return

        if (
            not deploy_config.service_name
            or not deploy_config.cluster_name
            or not deploy_config.vpc_id
        ):
            click.echo(
                "Error: deploy.enabled requires service_name, cluster_name, and vpc_id"
            )
            return

        # Validate subnet configuration
        if not deploy_config.alb_subnet_ids or not deploy_config.ecs_subnet_ids:
            click.echo(
                "Error: deploy.enabled requires both alb_subnet_ids and ecs_subnet_ids"
            )
            return
        
        if len(deploy_config.alb_subnet_ids) < 2:
            click.echo(
                "Error: deploy.enabled requires at least 2 ALB subnet IDs for load balancer"
            )
            return
        
        if len(deploy_config.ecs_subnet_ids) < 1:
            click.echo(
                "Error: deploy.enabled requires at least 1 ECS subnet ID for tasks"
            )
            return

    # Validate build requirements
    if build_config.push_to_ecr and not build_config.ecr_repository:
        click.echo("Error: ecr_repository is required when push_to_ecr is true")
        return

    # Execute build
    click.echo("Starting build process...")
    build_cmd = BuildCommand()
    
    # Determine parameters based on build mode
    if hasattr(build_config, 'entrypoint') and build_config.entrypoint:
        # Entrypoint mode
        build_cmd.execute(
            github_url=None,
            subfolder=None,
            image_name=build_config.image_name,
            ecr_repository=build_config.ecr_repository,
            aws_region=build_config.aws_region,
            dockerfile_path=build_config.dockerfile_path,
            push_to_ecr=build_config.push_to_ecr,
            branch=None,
            command_override=build_config.command_override,
            environment_variables=build_config.environment_variables,
            entrypoint_command=build_config.entrypoint.command,
            entrypoint_args=build_config.entrypoint.args,
            architecture=build_config.architecture,
        )
    else:
        # GitHub mode - validate that github config exists
        if not hasattr(build_config, 'github') or not build_config.github:
            click.echo("Error: Either entrypoint or github configuration must be specified")
            return
            
        build_cmd.execute(
            github_url=build_config.github.github_url,
            subfolder=build_config.github.subfolder,
            image_name=build_config.image_name,
            ecr_repository=build_config.ecr_repository,
            aws_region=build_config.aws_region,
            dockerfile_path=build_config.dockerfile_path,
            push_to_ecr=build_config.push_to_ecr,
            branch=build_config.github.branch,
            command_override=build_config.command_override,
            environment_variables=build_config.environment_variables,
            entrypoint_command=None,
            entrypoint_args=None,
            architecture=build_config.architecture,
        )

    # Execute deployment if enabled
    if deploy_config and deploy_config.enabled:
        click.echo("Starting deployment process...")

        # Use the image_uri from build config (always available now)
        image_uri = build_config.image_uri

        deploy_cmd = DeployCommand()
        alb_url = deploy_cmd.execute(
            image_uri=image_uri,
            service_name=deploy_config.service_name,
            cluster_name=deploy_config.cluster_name,
            aws_region=deploy_config.aws_region,
            port=deploy_config.port,
            cpu=deploy_config.cpu,
            memory=deploy_config.memory,
            vpc_id=deploy_config.vpc_id,
            alb_subnet_ids=deploy_config.alb_subnet_ids,
            ecs_subnet_ids=deploy_config.ecs_subnet_ids,
            certificate_arn=deploy_config.certificate_arn,
        )

        # Generate MCP configuration (always)
        from .mcp_config import MCPConfigGenerator

        config = MCPConfigGenerator.print_setup_instructions(
            deploy_config.service_name, alb_url
        )

        # Print configuration to stdout
        click.echo("\nMCP Client Configuration:")
        click.echo(config)

        # Save to file if requested
        if deploy_config.save_config:
            MCPConfigGenerator.save_config(config, deploy_config.save_config)
            click.echo(
                f"\nMCP configuration guide saved to: {deploy_config.save_config}"
            )

        click.echo(f"\nDeployment successful! ALB URL: {alb_url}")
    else:
        click.echo(
            "Build completed successfully! (Deployment skipped - deploy.enabled is false)"
        )


if __name__ == "__main__":
    cli()
