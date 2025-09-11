"""Dockerfile generation utilities for MCP server automation."""

import os
from typing import Optional, List, Dict, Any

from jinja2.sandbox import SandboxedEnvironment
import os.path


class DockerfileGenerator:
    """Handles generation of Dockerfiles from templates."""

    def generate_dockerfile(
        self,
        package_info: Dict[str, Any],
        custom_dockerfile_path: Optional[str] = None,
    ) -> str:
        """Generate Dockerfile based on template."""
        if custom_dockerfile_path:
            # Validate path to prevent traversal
            safe_path = self._validate_path(custom_dockerfile_path)
            if os.path.exists(safe_path):
                with open(safe_path, "r", encoding='utf-8') as f:
                    return f.read()

        # Generate the complete ENTRYPOINT command
        from .docker_handler import DockerHandler
        docker_handler = DockerHandler()
        package_info["entrypoint_command"] = docker_handler.generate_entrypoint_command(
            package_info["start_command"]
        )

        # Sanitize package_info to prevent injection
        safe_package_info = self._sanitize_package_info(package_info)
        
        # Load appropriate Dockerfile template based on language
        language = safe_package_info.get('language', 'python')
        if language not in ['python', 'nodejs']:
            language = 'python'
        template_filename = f"Dockerfile-{language}.j2"
        template_path = os.path.join(
            os.path.dirname(__file__), "templates", template_filename
        )
        with open(template_path, "r", encoding='utf-8') as f:
            template_content = f.read()

        # Use sandboxed environment to prevent SSTI
        env = SandboxedEnvironment()
        dockerfile_template = env.from_string(template_content)

        return dockerfile_template.render(package_info=safe_package_info)
    
    def _validate_path(self, path: str) -> str:
        """Validate file path to prevent traversal attacks."""
        # Convert to absolute path and resolve any .. components
        abs_path = os.path.abspath(path)
        # Ensure the path doesn't contain traversal attempts
        if '..' in path or abs_path != os.path.normpath(abs_path):
            raise ValueError(f"Invalid path detected: {path}")
        return abs_path
    
    def _sanitize_package_info(self, package_info: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize package info to prevent injection attacks."""
        import re
        safe_info = {}
        
        # Whitelist allowed keys and sanitize values
        allowed_keys = {
            'language', 'manager', 'requirements_file', 'project_file', 
            'start_command', 'environment_variables', 'entrypoint_command'
        }
        
        for key, value in package_info.items():
            if key in allowed_keys:
                if isinstance(value, str):
                    # Remove potentially dangerous characters
                    safe_info[key] = re.sub(r'[<>&"\']', '', str(value))
                elif isinstance(value, list):
                    # Sanitize list items
                    safe_info[key] = [re.sub(r'[<>&"\']', '', str(item)) for item in value]
                elif isinstance(value, dict):
                    # Sanitize dict values
                    safe_info[key] = {k: re.sub(r'[<>&"\']', '', str(v)) for k, v in value.items()}
                else:
                    safe_info[key] = value
        
        return safe_info