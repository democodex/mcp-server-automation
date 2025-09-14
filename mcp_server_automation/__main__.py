#!/usr/bin/env python3
"""Main entry point for MCP Server Automation CLI."""

import sys
import os


def main():
    """Main entry point for the CLI."""
    # Check if user wants multi-cloud CLI (new) or legacy CLI (backward compatibility)
    args = sys.argv[1:]

    # Use multi-cloud CLI if:
    # 1. --provider flag is used
    # 2. Environment variable MCP_USE_MULTI_CLOUD is set
    # 3. Configuration file contains 'cloud:' section (detected later)
    use_multi_cloud = (
        '--provider' in args or
        os.getenv('MCP_USE_MULTI_CLOUD', '').lower() in ('true', '1', 'yes')
    )

    # Check for --help or --version first (should work with both CLIs)
    if '--help' in args or '--version' in args:
        use_multi_cloud = True  # Use new CLI for help/version

    if use_multi_cloud:
        # Use new multi-cloud CLI
        from .multi_cloud_cli import multi_cloud_cli
        multi_cloud_cli()
    else:
        # Use legacy AWS-only CLI for backward compatibility
        from .cli import cli
        cli()


if __name__ == "__main__":
    main()
