# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP Server Automation CLI tool that automates the process of transforming Model Context Protocol (MCP) stdio servers into Docker images deployed on AWS ECS using mcp-proxy. The tool bridges the gap between local MCP servers and remote HTTP-based deployments.

## Common Commands

### Development Setup
```bash
# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Install in development mode (optional - for local CLI usage)
pip install -e .
```

### Build and Deploy MCP Servers

#### Using uv run (Recommended)
```bash
# Build MCP server using config file (entrypoint mode)
uv run python -m mcp_server_automation --config config-examples/entrypoint-example.yaml

# Build MCP server using direct command mode (no config file needed)
uv run python -m mcp_server_automation -- npx -y @modelcontextprotocol/server-everything

# Build and push to ECR using direct command mode
uv run python -m mcp_server_automation --push-to-ecr -- uvx mcp-server-automation

# Build for specific architecture using direct command mode
uv run python -m mcp_server_automation --arch linux/arm64 -- npx -y @modelcontextprotocol/server-everything

# Build MCP server from GitHub repository and push to ECR
uv run python -m mcp_server_automation --config config-examples/github-example.yaml

# Complete build and deployment to ECS
uv run python -m mcp_server_automation --config config-examples/full-deployment.yaml

# Install and run from GitHub repository using uvx
uvx --from git+https://github.com/awslabs/mcp-server-automation mcp-server-automation --config my-config.yaml
```

#### Using Python directly
```bash
# Build MCP server using config file (entrypoint mode)
python -m mcp_server_automation --config config-examples/entrypoint-example.yaml

# Build MCP server using direct command mode (no config file needed)
python -m mcp_server_automation -- npx -y @modelcontextprotocol/server-everything

# Build and push to ECR using direct command mode
python -m mcp_server_automation --push-to-ecr -- uvx mcp-server-automation

# Build for specific architecture using direct command mode
python -m mcp_server_automation --arch linux/arm64 -- npx -y @modelcontextprotocol/server-everything

# Build and push to ECR from GitHub repository
python -m mcp_server_automation --config config-examples/github-example.yaml

# Complete build and deployment workflow
python -m mcp_server_automation --config config-examples/full-deployment.yaml
```

#### Using local development setup
```bash
# Install in development mode
pip install -e .

# Use the CLI directly with config file
mcp-automate --config config-examples/entrypoint-example.yaml

# Use the CLI directly with command mode
mcp-automate -- npx -y @modelcontextprotocol/server-everything

# Use the CLI with push to ECR
mcp-automate --push-to-ecr -- uvx mcp-server-automation

# Use the CLI with specific architecture
mcp-automate --arch linux/arm64 -- npx -y @modelcontextprotocol/server-everything
```

### Testing with MCP Inspector
```bash
# Test built Docker containers (using dynamic tags)
docker run -p 8000:8000 mcp-local/mcp-src-aws-documentation-mcp-server:a1b2c3d4-20231222-143055

# Use MCP inspector to test endpoints (updated to /mcp endpoint)
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

## Architecture

### Core Components

1. **BuildCommand** (`build.py`): Handles fetching MCP servers from GitHub, analyzing dependencies, generating Dockerfiles, and building/pushing images
2. **DeployCommand** (`deploy.py`): Manages ECS deployment using CloudFormation templates with ALB configuration  
3. **ConfigLoader** (`config.py`): Parses YAML configuration files with build and deploy specifications
4. **MCPConfigGenerator** (`mcp_config.py`): Generates client configuration for Claude Desktop, Cline, and other MCP clients

### Build Process Flow

#### Direct Command Mode (No Config File)
1. **Command Parsing**: Parses command and arguments from CLI using `--` separator (e.g., `-- npx -y @modelcontextprotocol/server-everything`)
2. **Package Name Extraction**: Automatically extracts package names for Docker image naming (e.g., `@modelcontextprotocol/server-everything` → `mcp-server-everything`)
3. **Language Detection**: Detects runtime (Node.js/Python) from command
4. **Dockerfile Generation**: Creates optimized containers with pre-installed packages
5. **Image Building**: Builds container ready to execute the specified command

#### Entrypoint Mode (Config File)
1. **Command Processing**: Uses provided command and arguments from YAML configuration
2. **Language Detection**: Detects runtime (Node.js/Python) from command
3. **Dockerfile Generation**: Creates optimized containers with pre-installed packages
4. **Image Building**: Builds container ready to execute the specified command

#### GitHub Mode (Config File)  
1. **Repository Analysis**: Downloads GitHub repos and detects MCP server configuration from README files
2. **Command Detection**: Parses JSON blocks in README files to extract MCP server start commands, prioritizing NPX/uvx over Docker commands
3. **Dockerfile Generation**: Uses Jinja2 templates to create multi-stage Docker builds with mcp-proxy CLI integration
4. **Image Building**: Creates hybrid Node.js + Python containers with proper dependency management

### Key Technical Details

- **mcp-proxy Integration**: Uses TypeScript/Node.js CLI tool from https://github.com/punkpeye/mcp-proxy for HTTP transport
- **Container Architecture**: Multi-stage builds with `node:24-bullseye` base image, includes netcat for health checks
- **Command Format**: `mcp-proxy --port 8000 --shell <command> -- <args>` for proper argument ordering
- **Transport Protocol**: Converts MCP stdio to HTTP with `/mcp` endpoint for Streamable HTTP transport
- **Dynamic Tagging**: Images tagged with git commit hash and timestamp (e.g., `a1b2c3d4-20231222-143055`)
- **Branch Support**: Can build from specific git branches, defaults to 'main'

### Configuration System

The tool supports three build approaches:

#### 1. Direct Command Mode (No Config File)
- **CLI Usage**: `mcp-server-automation --push-to-ecr -- npx -y @modelcontextprotocol/server-everything`
- **Features**: 
  - No configuration file needed
  - Uses `--` separator to specify command and arguments
  - Automatic package name extraction for image naming
  - Optional `--push-to-ecr` flag for ECR deployment
  - Build-only mode (no deployment support)

#### 2. Config File Modes
Uses YAML files with separate `build` and `deploy` sections supporting two build modes:

**Build Section:**
- **Entrypoint Mode**: Direct command execution (e.g., `npx`, `uvx`) 
- **GitHub Mode**: Repository-based builds with branch selection
- **Common Options**: Image naming, ECR settings, environment variables

**Deploy Section:**
- ECS cluster, VPC/subnet configuration, resource sizing, SSL certificates, MCP config generation

### Multi-Architecture Support

The tool supports building Docker images for specific target architectures using the `architecture` parameter in the build configuration. This enables cross-platform builds for different CPU architectures.

#### Supported Architectures
- `linux/amd64` - Standard x86-64 architecture (Intel/AMD)
- `linux/arm64` - ARM 64-bit architecture (Apple Silicon, AWS Graviton)
- `linux/arm/v7` - ARM 32-bit architecture

#### Docker Buildx Setup

Multi-architecture builds require Docker Buildx. If you encounter build errors with the `architecture` parameter, set up Buildx:

```bash
# Create and use a new multi-platform builder
docker buildx create --name multiarch --use

# Or use an existing builder
docker buildx use <builder-name>

# List available builders
docker buildx ls
```

#### Configuration Example

```yaml
build:
  github:
    github_url: "https://github.com/modelcontextprotocol/servers"
    subfolder: "src/everything"
  architecture: "linux/arm64"  # Build for ARM64 architecture
  push_to_ecr: true
```

### Infrastructure Deployment

- **CloudFormation**: Complete infrastructure as code with VPC, ALB, ECS Fargate service
- **Security Groups**: Proper network isolation between ALB and ECS tasks
- **Health Checks**: Container uses netcat port checking, ALB health checks `/mcp` endpoint expecting HTTP 400
- **Session Stickiness**: ALB cookie-based stickiness for MCP client compatibility
- **Error Handling**: Graceful handling of CloudFormation "No updates" errors

## File Structure

### Core Modules
- `build.py`: Main build orchestration and workflow management
- `deploy.py`: ECS deployment with CloudFormation stack management  
- `cli.py`: Click-based CLI interface with build/deploy commands
- `config.py`: YAML configuration parsing with auto-generation features
- `mcp_config.py`: Client configuration generation for deployed services

### Specialized Components
- `github_handler.py`: GitHub repository fetching and extraction
- `package_detector.py`: Language detection and package manager identification
- `command_parser.py`: Command extraction from README, pyproject.toml, setup.py
- `docker_handler.py`: Docker image building and ECR operations
- `dockerfile_generator.py`: Dockerfile generation from templates
- `utils.py`: Common utility functions and helpers

### Templates and Configuration
- `templates/Dockerfile-nodejs.j2`: Node.js Docker template
- `templates/Dockerfile-python.j2`: Python Docker template
- `templates/ecs-service.yaml`: CloudFormation template for AWS infrastructure

## Testing

The project includes test configurations primarily for AWS documentation MCP server:
- `test-aws-docs.yaml`: Configuration for AWS documentation MCP server (recommended)
- `test-filesystem-reference.yaml`: Reference configuration for filesystem MCP server (has Node.js argument handling issues)

Use `test-aws-docs.yaml` for validation when making changes to the build or deployment logic. The AWS Documentation MCP Server is more reliable than the filesystem server due to Python-based implementation vs Node.js argument parsing complexities.

## Configuration Options

### Build Section

Choose **ONE** of these two methods:

#### Method 1: Entrypoint Mode (Direct Commands)
```yaml
build:
  entrypoint:
    command: "npx"  # or "uvx", "uv", etc.
    args: 
      - "-y"
      - "@modelcontextprotocol/server-everything"
```

#### Method 2: GitHub Mode (Repository-based)
```yaml
build:
  github:
    github_url: "https://github.com/modelcontextprotocol/servers"
    subfolder: "src/everything"  # optional
    branch: "main"              # optional, defaults to 'main'
```

#### Common Build Options
- `push_to_ecr`: Whether to push to ECR registry (boolean)
- `aws_region`: AWS region for ECR (optional, defaults to profile region)
- `dockerfile_path`: Custom Dockerfile path (optional)
- `command_override`: Override detected start command (optional)
- `environment_variables`: Container environment variables (optional)
- `architecture`: Target platform/architecture for Docker build (optional, e.g., "linux/amd64", "linux/arm64")
- `image`: Custom image configuration (optional)
  - `repository`: Full image repository URL
  - `tag`: Image tag

### Deploy Section
- `enabled`: Whether to deploy to ECS
- `service_name`: ECS service name
- `cluster_name`: ECS cluster name
- `vpc_id`: VPC ID for deployment
- `alb_subnet_ids`: Public subnet IDs for ALB (minimum 2)
- `ecs_subnet_ids`: Private subnet IDs for ECS tasks (minimum 1)
- `save_config`: File path to save MCP client configuration (optional)
- `certificate_arn`: SSL certificate ARN for HTTPS (optional)