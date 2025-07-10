# Configuration Guide

This guide explains how to configure the MCP Server Automation CLI for building and deploying MCP servers.

## Configuration Structure

The configuration file uses YAML format with two main sections:
- `build`: Defines how to build the Docker image
- `deploy`: Defines deployment settings (optional)

## Build Configuration

You must choose **ONE** of two build methods:

### Method 1: Entrypoint Mode (Direct Commands)

Use this method when you want to run MCP servers using direct commands like `npx` or `uvx`:

```yaml
build:
  entrypoint:
    command: "npx"  # or "uvx", "uv", etc.
    args: 
      - "-y"
      - "@modelcontextprotocol/server-everything"
```

**Supported Commands:**
- `npx`: Node.js package execution
- `uvx`: UV package execution (Python)
- `uv`: UV with run command
- `python`/`python3`: Direct Python execution

### Method 2: GitHub Mode (Repository-based)

Use this method when you want to build from a GitHub repository:

```yaml
build:
  github:
    github_url: "https://github.com/modelcontextprotocol/servers"
    subfolder: "src/everything"  # optional
    branch: "main"              # optional, defaults to 'main'
```

## Common Build Options

Both methods support these additional options:

```yaml
build:
  # ... method configuration above ...
  
  # Push to ECR (required for deployment)
  push_to_ecr: true
  
  # AWS region (optional, defaults to profile region)
  aws_region: "us-east-1"
  
  # Custom Dockerfile path (optional)
  dockerfile_path: "./custom.Dockerfile"
  
  # Override detected command (optional)
  command_override:
    - "python"
    - "-m"
    - "my_server"
  
  # Environment variables (optional)
  environment_variables:
    LOG_LEVEL: "debug"
    API_KEY: "your-key"
  
  # Custom image configuration (optional)
  image:
    repository: "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo"
    tag: "latest"
```

## Deploy Configuration

The deploy section is optional and controls ECS deployment:

```yaml
deploy:
  enabled: true  # Set to false to skip deployment
  
  # Required settings
  service_name: "my-mcp-server"
  cluster_name: "my-ecs-cluster"
  vpc_id: "vpc-12345678"
  
  # Network configuration
  alb_subnet_ids:    # Public subnets (minimum 2)
    - "subnet-public-1"
    - "subnet-public-2"
  ecs_subnet_ids:    # Private or public subnets (minimum 1)
    - "subnet-private-1"
    - "subnet-private-2"
  
  # Resource configuration (optional)
  cpu: 256          # CPU units (default: 256)
  memory: 512       # Memory in MB (default: 512)
  port: 8000        # Container port (default: 8000)
  
  # SSL certificate (optional)
  certificate_arn: "arn:aws:acm:us-east-1:123456789012:certificate/my-cert"
  
  # Save client configuration (optional)
  save_config: "./mcp-config.md"
```

## Example Configurations

### Local Development (Entrypoint)
```yaml
build:
  entrypoint:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-everything"]
  push_to_ecr: false

deploy:
  enabled: false
```

### Production Deployment (GitHub)
```yaml
build:
  github:
    github_url: "https://github.com/modelcontextprotocol/servers"
    subfolder: "src/everything"
  push_to_ecr: true
  aws_region: "us-east-1"

deploy:
  enabled: true
  service_name: "prod-mcp-server"
  cluster_name: "production"
  vpc_id: "vpc-prod123"
  alb_subnet_ids: ["subnet-pub-1", "subnet-pub-2"]
  ecs_subnet_ids: ["subnet-priv-1", "subnet-priv-2"]
  cpu: 512
  memory: 1024
  certificate_arn: "arn:aws:acm:us-east-1:123456789012:certificate/prod"
```

## Usage

```bash
# Using uv (recommended)
uv run python -m mcp_server_automation --config my-config.yaml

# Using Python directly
python -m mcp_server_automation --config my-config.yaml

# Using uvx from GitHub
uvx --from git+https://github.com/awslabs/mcp-server-automation mcp-server-automation --config my-config.yaml
```

## Error Handling

The tool validates your configuration and will show clear error messages if:
- Both `entrypoint` and `github` are specified
- Neither `entrypoint` nor `github` are specified
- Required deployment fields are missing when `deploy.enabled: true`
- ECR push is disabled but deployment is enabled

## Image Naming

- **Entrypoint mode**: `mcp-<command>` (e.g., `mcp-npx`, `mcp-uvx`)
- **GitHub mode**: `<repo-name>-<subfolder>` (e.g., `servers-src-everything`)
- **Custom**: Use `image.repository` to specify exact names

## Tags

- **Entrypoint mode**: `entrypoint-YYYYMMDD-HHMMSS`
- **GitHub mode**: `<git-hash>-YYYYMMDD-HHMMSS`
- **Custom**: Use `image.tag` to specify exact tags