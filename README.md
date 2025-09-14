# MCP Server Automation CLI

A powerful CLI tool that automates the process of transforming Model Context Protocol (MCP) stdio servers into Docker images deployed on AWS ECS and Google Cloud Run using [mcp-proxy](https://github.com/punkpeye/mcp-proxy). This tool bridges the gap between local MCP servers and remote HTTP-based deployments.

## 🚀 Features

- **☁️ Multi-Cloud Support**: Deploy to both AWS ECS and Google Cloud Run with unified configuration
- **⚡ Direct Command Mode**: Build MCP servers instantly without config files using `--` separator syntax
- **🔄 Automatic Build**: Fetch MCP servers from GitHub, build Docker images, and push to container registries
- **🚀 One-Click Deploy**: Generate infrastructure templates and deploy complete container services
- **📦 Optional Dependencies**: Install only the cloud provider dependencies you need
- **🔍 Smart Detection**: Automatically detect MCP server commands from README files
- **🐳 Multi-Language**: Support for Python and Node.js/TypeScript MCP servers with automatic language detection
- **🏷️ Smart Naming**: Automatic package name extraction for Docker image naming
- **🔧 Debug Support**: Built-in debug logging for troubleshooting
- **📝 Config Generation**: Generate MCP client configurations for Claude Desktop, Cline, etc.

## 📦 Installation

### Choose Your Cloud Provider

Install only the dependencies you need:

```bash
# AWS-only installation (smaller, faster)
pip install 'mcp-server-automation[aws]'

# Google Cloud-only installation
pip install 'mcp-server-automation[gcp]'

# Multi-cloud installation (both AWS and GCP)
pip install 'mcp-server-automation[all]'

# Base installation (no cloud providers - build only)
pip install mcp-server-automation
```

### Legacy Installation
For backward compatibility with existing workflows:
```bash
pip install 'mcp-server-automation[legacy]'  # AWS-only (original behavior)
```

## 📋 Prerequisites

### Common Requirements
- **Python 3.8+**
- **Docker** (with daemon running)

### AWS Prerequisites (if using AWS provider)
- **AWS CLI** configured with appropriate permissions
- **AWS ECR repository** (auto-created if needed)
- **AWS ECS cluster** (specified in deployment config)

### GCP Prerequisites (if using GCP provider)
- **Google Cloud CLI (gcloud)** installed and configured
- **GCP project** with required APIs enabled:
  - Cloud Run API
  - Artifact Registry API
- **Proper IAM permissions** (Cloud Run Admin, Artifact Registry Admin)


## 📖 Quick Start

### AWS Deployment

```bash
# Build and deploy to AWS ECS
mcp-server-automation --provider aws --config aws-config.yaml

# Direct command mode (AWS)
mcp-server-automation --provider aws --push-to-registry -- npx -y @modelcontextprotocol/server-everything
```

### Google Cloud Deployment

```bash
# Build and deploy to Google Cloud Run
mcp-server-automation --provider gcp --project-id my-project --config gcp-config.yaml

# Direct command mode (GCP)
mcp-server-automation --provider gcp --project-id my-project --push-to-registry -- uvx mcp-server
```

### Legacy AWS Mode (Backward Compatibility)

```bash
# Original AWS-only commands (still supported)
mcp-server-automation --config config.yaml
mcp-server-automation --push-to-ecr -- npx -y @modelcontextprotocol/server-everything
```

### Config Files

Use yaml-based config file with configuration files for complex deployments:

```bash
# Install from a Git repository
uvx --from git+https://github.com/aws-samples/sample-mcp-server-automation mcp-server-automation --config your-config.yaml
```

### Local Development Setup (MacOS or Linux)

```bash
# Clone and setup
git clone https://github.com/aws-samples/sample-mcp-server-automation
cd mcp-convert-automate
uv sync
source .venv/bin/activate

# Run with config file
uv run mcp-server-automation --config your-config.yaml

# Run with direct command mode
uv run mcp-server-automation -- npx -y @modelcontextprotocol/server-everything

# Run with specific architecture
uv run mcp-server-automation --arch linux/arm64 -- npx -y @modelcontextprotocol/server-everything
```

## ⚙️ Configuration

The tool supports two modes:

1. **Direct Command Mode**: No configuration file needed - specify command directly with `--` separator
2. **Config File Mode**: Use YAML configuration files for complex builds and deployments

### Direct Command Mode

Use the `--` separator to specify commands directly:

```bash
# Basic usage
mcp-server-automation -- npx -y @modelcontextprotocol/server-everything

# With ECR push (requires ECR repository to be configured separately)
mcp-server-automation --push-to-ecr -- python -m my_server

# With specific architecture for cross-platform builds
mcp-server-automation --arch linux/arm64 -- npx -y @modelcontextprotocol/server-everything

# Package name extraction for image naming
# @modelcontextprotocol/server-everything → mcp-server-everything
# mcp-server-automation → mcp-mcp-server-automation
```

**Features:**

- No config file required
- Automatic package name extraction for Docker image naming
- Multi-architecture support with `--arch` parameter (linux/amd64, linux/arm64, etc.)
- Build-only mode (deployment requires config files)
- Simple `--push-to-ecr` flag support

### Config File Mode

For complex scenarios, use YAML configuration files with `build` and `deploy` sections:

```yaml
build:
  # Method 1: Use command and package manager
  entrypoint:
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-everything"

  # Method 2: Fetch MCP server from GitHub
  # github:
    # Required: GitHub repository URL for MCP server
    # github_url: "https://github.com/awslabs/mcp"

    # Optional: Subfolder path if MCP server is not in root
    # subfolder: "src/aws-documentation-mcp-server"

    # Optional: Git branch to build from (default: main)
    # branch: "develop"

  # Required for deployment: Must be true to enable ECR push and deployment
  push_to_ecr: true

  # Optional: Custom Docker image configuration
  # If not specified, auto-generated when push_to_ecr=true
  # image:
  #   repository: "123456789012.dkr.ecr.us-east-1.amazonaws.com/mcp-servers/my-mcp-server"
  #   tag: "v1.0"  # Optional, defaults to dynamic git-based tag

  # Optional: AWS region (default: from AWS profile, fallback to us-east-1)
  # aws_region: "us-west-2"

  # Optional: Custom Dockerfile path
  # dockerfile_path: "./custom.Dockerfile"

  # Optional: Override auto-detected MCP server command
  # Required when README only contains Docker commands or no suitable command is found
  # command_override:
  #   - "python"
  #   - "-m"
  #   - "my_server_module"
  #   - "--verbose"

  # Optional: Set environment variables in the container
  # environment_variables:
  #   LOG_LEVEL: "debug"
  #   AWS_REGION: "us-east-1"
  #   MCP_SERVER_NAME: "custom-server"

  # Optional: Target architecture for Docker build
  # architecture: "linux/arm64"  # Options: linux/amd64, linux/arm64

deploy:
  # Required: Enable deployment (only works when push_to_ecr=true)
  enabled: true

  # Required: ECS service name
  service_name: "my-mcp-service"

  # Required: ECS cluster name
  cluster_name: "my-ecs-cluster"

  # Required: VPC ID where resources will be created
  vpc_id: "vpc-12345678"

  # Required: Subnet configuration
  alb_subnet_ids:    # Public subnets for ALB (minimum 2 in different AZs)
    - "subnet-public-1"
    - "subnet-public-2"
  ecs_subnet_ids:    # Private subnets for ECS tasks (minimum 1, should resides in AZ of alb_subnet_ids)
    - "subnet-private-1"
    - "subnet-private-2"

  # Optional: Container port (default: 8000)
  port: 8000

  # Optional: Task CPU units (default: 256)
  cpu: 256

  # Optional: Task memory in MB (default: 512)
  memory: 512

  # Optional: SSL certificate ARN for HTTPS
  certificate_arn: "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"

  # Optional: Save MCP client configuration to file
  save_config: "./mcp-config.json"
```

## 🔧 Advanced Usage

### Custom Dockerfile

```yaml
build:
  github_url: "https://github.com/my-org/custom-mcp-server"
  dockerfile_path: "./custom/Dockerfile"
  push_to_ecr: true
deploy:
  enabled: true
  # ... deployment configuration
```

### Environment Variables in Container

Set custom environment variables that will be available to the MCP server at runtime:

```yaml
build:
  github_url: "https://github.com/my-org/custom-mcp-server"
  environment_variables:
    LOG_LEVEL: "debug"
    AWS_REGION: "us-east-1"
    MCP_SERVER_NAME: "custom-server"
    PYTHONPATH: "/app/mcp-server:/custom/path"
  push_to_ecr: true
```

### System Environment Variables

Set environment variables to override default AWS settings:

```bash
export AWS_REGION=us-west-2
export ECS_CLUSTER_NAME=my-production-cluster
```

## 🏗️ Architecture

### Build Process Flow

The tool supports two build modes:

#### Direct Command Mode

1. **Command Parsing**: Parses command and arguments from CLI using `--` separator (e.g., `-- npx -y @modelcontextprotocol/server-everything`)
2. **Package Name Extraction**: Automatically extracts package names for Docker image naming (e.g., `@modelcontextprotocol/server-everything` → `mcp-server-everything`)
3. **Language Detection**: Detects runtime (Node.js/Python) from command
4. **Dockerfile Generation**: Creates optimized containers with pre-installed packages
5. **Image Building**: Builds container ready to execute the specified command

#### Config File Mode (GitHub/Entrypoint)

1. **Repository Analysis**: Downloads GitHub repos and detects MCP server configuration from README files (GitHub mode)
2. **Language Detection**: Automatically detects Python or Node.js/TypeScript based on project files (package.json, pyproject.toml, etc.)
3. **Command Detection**: Parses JSON blocks in README files to extract MCP server start commands from both Claude Desktop (`mcpServers`) and VS Code (`mcp.servers`) configuration formats
4. **Dockerfile Generation**: Uses language-specific Jinja2 templates (Dockerfile-python.j2, Dockerfile-nodejs.j2) to create optimized builds with mcp-proxy CLI integration
5. **Image Building**: Creates language-specific containers with proper dependency management and multi-stage builds

### Deployment Architecture

```
GitHub Repo → Docker Build → ECR → ECS Fargate ← ALB ← Internet
     ↓              ↓           ↓         ↓        ↓
MCP Server → mcp-proxy + MCP → Image → Service → HTTP/SSE Endpoints
```

### Language Support and Detection

The tool supports both **Python** and **Node.js/TypeScript** MCP servers with automatic language detection:

#### Python Projects

- Detected by: `pyproject.toml`, `requirements.txt`, `setup.py`, or `.py` files
- Package managers: pip, uv, poetry (automatically detected)
- Base image: `python:3.12-slim-bookworm`
- Command extraction from: console scripts in pyproject.toml, setup.py entry points

#### Node.js/TypeScript Projects

- Detected by: `package.json`, `tsconfig.json`, or `.ts/.js` files
- Package manager: npm (with Node.js 24-bullseye base image)
- Base image: `node:24-bullseye`
- Command extraction from: README JSON configurations

### Command Detection and Override

The tool automatically detects MCP server startup commands from:

1. **README files** - JSON configuration blocks supporting both formats:
   - Claude Desktop: `{"mcpServers": {...}}`
   - VS Code: `{"mcp": {"servers": {...}}}`
2. **Python projects** - `pyproject.toml` console scripts, `setup.py` entry points
3. **Node.js projects** - README configurations (package.json scripts not parsed)

**Command Override Required When:**

- README only contains Docker commands (not suitable for containerization)
- No suitable startup command can be detected
- You want to specify exact startup parameters

**Example:**

```yaml
build:
  github:
    github_url: "https://github.com/my-org/custom-mcp-server"
  command_override:
    - "python"
    - "-m"
    - "my_server_module"
    - "--verbose"
    - "--port"
    - "3000"
  push_to_ecr: true
```

**Example README Configurations Supported:**

Claude Desktop format:

```json
{
  "mcpServers": {
    "everything": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-everything"]
    }
  }
}
```

VS Code format:

```json
{
  "mcp": {
    "servers": {
      "everything": {
        "command": "python",
        "args": ["-m", "server"]
      }
    }
  }
}
```

**Error Example:**

If your MCP server README only shows Docker commands:

```json
{
  "mcpServers": {
    "myserver": {
      "command": "docker",
      "args": ["run", "myserver:latest"]
    }
  }
}
```

You'll get an error requiring `command_override` to specify the direct startup command.

## 🐛 Troubleshooting

### Docker Build Issues

- Ensure Docker daemon is running
- Check that the MCP server has proper dependency files (requirements.txt, pyproject.toml, etc.)
- Verify GitHub repository URL is accessible

### Multi-Architecture Build Issues

When using the `--arch` parameter or `architecture` in config files, you may encounter:

**Error: "No builder available for architecture"**

This means Docker Buildx is not properly configured. To fix:

```bash
# Create and use a new multi-platform builder
docker buildx create --name multiarch --use

# Or use an existing builder
docker buildx use <builder-name>

# List available builders
docker buildx ls
```

**Supported architectures:**
- `linux/amd64` - Standard x86-64 (Intel/AMD)
- `linux/arm64` - ARM 64-bit (Apple Silicon, AWS Graviton)

For more information, visit: https://docs.docker.com/build/building/multi-platform/

### ECR Push Issues

- Ensure AWS credentials have ECR permissions
- Verify ECR repository exists and is accessible
- Check that Docker is authenticated with ECR

### CloudFormation Deployment Issues

- Ensure AWS credentials have sufficient permissions
- Check that the ECS cluster exists
- Verify AWS region is correct
- Review CloudFormation events in AWS Console for detailed error messages

### MCP Server Connection Issues

- Check container logs in local setup: `docker logs <container-id>`
- Verify health check endpoint: `curl http://<alb-url>/mcp` (expects HTTP 400)
- Test direct connection: `curl http://<alb-url>/mcp`
- Use debug mode for detailed logging

## 🔐 AWS Permissions Required

The AWS credentials used must have the following permissions:

### ECR Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:GetAuthorizationToken",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    }
  ]
}
```

### ECS and CloudFormation Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:*",
        "cloudformation:*",
        "ec2:*",
        "elasticloadbalancing:*",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole",
        "logs:CreateLogGroup",
        "logs:DescribeLogGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

## 📝 MCP Client Configuration

After deployment, the tool generates configuration for MCP clients:

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "type": "sse",
      "url": "http://<ALB address>/sse"
    }
  }
}
```

### Testing MCP Connection

```bash
# Install mcp-proxy client
npm install -g mcp-proxy

# Test connection
mcp-proxy https://your-alb-url.amazonaws.com/mcp
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

## 🆘 Support

- Check the [troubleshooting section](#-troubleshooting) for common issues
- Review CloudFormation events in AWS Console for deployment issues
- Use debug mode for detailed logging
- Open an issue for bugs or feature requests
