"""Dockerfile generation utilities for MCP server automation."""

import os
from typing import Optional, List, Dict, Any

from jinja2 import Template


class DockerfileGenerator:
    """Handles generation of Dockerfiles from templates."""

    def generate_dockerfile(
        self,
        package_info: Dict[str, Any],
        custom_dockerfile_path: Optional[str] = None,
    ) -> str:
        """Generate Dockerfile based on template."""
        if custom_dockerfile_path and os.path.exists(custom_dockerfile_path):
            with open(custom_dockerfile_path, "r", encoding='utf-8') as f:
                return f.read()

        # Generate the complete ENTRYPOINT command
        from .docker_handler import DockerHandler
        docker_handler = DockerHandler()
        package_info["entrypoint_command"] = docker_handler.generate_entrypoint_command(
            package_info["start_command"]
        )

        # Load appropriate Dockerfile template based on language
        template_filename = f"Dockerfile-{package_info['language']}.j2"
        template_path = os.path.join(
            os.path.dirname(__file__), "templates", template_filename
        )
        with open(template_path, "r", encoding='utf-8') as f:
            template_content = f.read()

        dockerfile_template = Template(template_content)

        return dockerfile_template.render(package_info=package_info)