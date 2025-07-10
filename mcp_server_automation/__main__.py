#!/usr/bin/env python3
"""Main entry point for MCP Server Automation CLI."""


def main():
    """Main entry point for the CLI."""
    from .cli import cli
    cli()


if __name__ == "__main__":
    main()
