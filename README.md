# MCP Server Automation CLI

A powerful CLI tool that automates the process of transforming Model Context Protocol (MCP) stdio servers into containerized services deployed on **AWS ECS** and **Google Cloud Run** using [mcp-proxy](https://github.com/punkpeye/mcp-proxy). This tool bridges the gap between local MCP servers and remote HTTP-based deployments.

## 🚀 Features

- **☁️ Multi-Cloud Support**: Deploy to both AWS ECS and Google Cloud Run with unified configuration
- **📦 Optional Dependencies**: Install only the cloud provider dependencies you need
- **⚡ Direct Command Mode**: Build MCP servers instantly without config files using `--` separator syntax
- **🔄 Automatic Build**: Fetch MCP servers from GitHub, build Docker images, and push to container registries
- **🚀 One-Click Deploy**: Generate infrastructure templates and deploy complete container services
- **🔍 Smart Detection**: Automatically detect MCP server commands from README files
- **🐳 Multi-Language**: Support for Python and Node.js/TypeScript MCP servers with automatic language detection
- **🏷️ Smart Naming**: Automatic package name extraction for Docker image naming
- **🔧 Debug Support**: Built-in debug logging for troubleshooting
- **📝 Config Generation**: Generate MCP client configurations for Claude Desktop, Cline, etc.

## 📦 Installation

> **Note:** This package will be published to PyPI soon. For now, install from source.

### Current Installation (From Source)

```bash
# Clone the repository
git clone https://github.com/your-org/mcp-server-automation.git
cd mcp-server-automation

# Install with your preferred cloud provider dependencies
pip install -e ".[aws]"      # AWS-only (35MB, fastest for AWS users)
pip install -e ".[gcp]"      # Google Cloud-only (40MB, fastest for GCP users)
pip install -e ".[all]"      # Multi-cloud (70MB, both AWS and GCP)
pip install -e .             # Base installation (20MB, build-only, no cloud deployment)
```

### Future Installation (After PyPI Publication)

```bash
# These commands will work once published to PyPI
pip install 'mcp-server-automation[aws]'    # AWS-only
pip install 'mcp-server-automation[gcp]'    # GCP-only
pip install 'mcp-server-automation[all]'    # Multi-cloud
pip install mcp-server-automation           # Base installation
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

## 🎮 Usage

### ⚡ Quick Start - Direct Command Mode

#### AWS Examples
```bash
# Build MCP server (no deployment)
mcp-server-automation --provider aws -- npx -y @modelcontextprotocol/server-everything

# Build + push to ECR
mcp-server-automation --provider aws --push-to-registry -- npx -y @modelcontextprotocol/server-everything

# Build for ARM64 architecture
mcp-server-automation --provider aws --arch linux/arm64 --push-to-registry -- python -m server
```

#### Google Cloud Examples
```bash
# Build MCP server (no deployment)
mcp-server-automation --provider gcp --project-id my-project -- uvx mcp-server

# Build + push to Artifact Registry
mcp-server-automation --provider gcp --project-id my-project --push-to-registry -- python -m server

# Specific region deployment
mcp-server-automation --provider gcp --project-id my-project --region europe-west1 --push-to-registry -- uvx server
```

### ⚙️ Advanced - Configuration File Mode

#### AWS ECS Full Deployment

**Create `aws-config.yaml`:**
```yaml
cloud:
  provider: "aws"
  region: "us-east-1"

build:
  github:
    github_url: "https://github.com/modelcontextprotocol/servers"
    subfolder: "src/everything"
  push_to_registry: true

deploy:
  enabled: true
  service_name: "mcp-everything"
  aws:
    cluster_name: "production-cluster"
    vpc_id: "vpc-12345678"
    alb_subnet_ids: ["subnet-pub-1", "subnet-pub-2"]  # Public subnets (min 2)
    ecs_subnet_ids: ["subnet-priv-1"]                 # Private subnets (min 1)
    certificate_arn: "arn:aws:acm:us-east-1:123456789012:certificate/abc123"
  save_config: "./mcp-client-config.json"
```

**Deploy:**
```bash
mcp-server-automation --provider aws --config aws-config.yaml
```

#### Google Cloud Run Full Deployment

**Create `gcp-config.yaml`:**
```yaml
cloud:
  provider: "gcp"
  region: "us-central1"
  project_id: "my-gcp-project"

build:
  entrypoint:
    command: "python"
    args: ["-m", "my_mcp_server"]
  push_to_registry: true
  environment_variables:
    LOG_LEVEL: "info"

deploy:
  enabled: true
  service_name: "my-mcp-server"
  gcp:
    allow_unauthenticated: true
    max_instances: 20
    cpu_limit: "2000m"      # 2 CPU cores
    memory_limit: "2Gi"     # 2GB RAM
    custom_domain: "mcp.example.com"
  save_config: "./mcp-client-config.json"
```

**Deploy:**
```bash
mcp-server-automation --provider gcp --config gcp-config.yaml
```

### 🔄 Backward Compatibility (AWS-Only Mode)

Existing AWS-only commands continue to work unchanged:

```bash
# Original commands still supported
mcp-server-automation --config config.yaml
mcp-server-automation --push-to-ecr -- npx -y @modelcontextprotocol/server-everything
```

## 🛠️ Configuration Reference

### Build Configuration

```yaml
build:
  # Option 1: GitHub repository
  github:
    github_url: "https://github.com/user/repo"
    subfolder: "path/to/server"    # Optional
    branch: "main"                 # Optional

  # Option 2: Direct command
  entrypoint:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-everything"]

  # Common options
  push_to_registry: true           # Push to ECR/Artifact Registry
  architecture: "linux/arm64"     # Target architecture
  environment_variables:          # Container environment
    LOG_LEVEL: "debug"
```

### Deployment Configuration

#### AWS ECS
```yaml
deploy:
  enabled: true
  service_name: "my-service"
  aws:
    cluster_name: "my-cluster"                    # Required
    vpc_id: "vpc-12345678"                        # Required
    alb_subnet_ids: ["subnet-1", "subnet-2"]     # Public subnets (min 2)
    ecs_subnet_ids: ["subnet-3"]                 # Private subnets (min 1)
    certificate_arn: "arn:aws:acm:..."           # Optional HTTPS
  save_config: "./client-config.json"            # Optional
```

#### Google Cloud Run
```yaml
deploy:
  enabled: true
  service_name: "my-service"
  gcp:
    allow_unauthenticated: true                   # Public access
    max_instances: 100                            # Max containers
    cpu_limit: "1000m"                            # 1 CPU core
    memory_limit: "512Mi"                         # 512MB RAM
    custom_domain: "api.example.com"              # Optional
    ingress: "all"                                # Traffic source
  save_config: "./client-config.json"            # Optional
```

## 🎯 Real-World Examples

### Deploy AWS Documentation MCP Server

```bash
# Quick deployment
mcp-server-automation --provider aws --push-to-registry -- npx -y @modelcontextprotocol/server-everything

# Production deployment with HTTPS
cat > production-aws.yaml << EOF
cloud:
  provider: "aws"
  region: "us-east-1"

build:
  github:
    github_url: "https://github.com/modelcontextprotocol/servers"
    subfolder: "src/everything"
  push_to_registry: true

deploy:
  enabled: true
  service_name: "aws-docs-mcp"
  aws:
    cluster_name: "production"
    vpc_id: "vpc-prod123"
    alb_subnet_ids: ["subnet-pub1", "subnet-pub2"]
    ecs_subnet_ids: ["subnet-priv1"]
    certificate_arn: "arn:aws:acm:us-east-1:123456789012:certificate/prod"
  save_config: "./aws-docs-mcp-config.json"
EOF

mcp-server-automation --provider aws --config production-aws.yaml
```

### Deploy Custom Python Server to Cloud Run

```bash
cat > python-gcp.yaml << EOF
cloud:
  provider: "gcp"
  region: "us-central1"
  project_id: "my-ai-project"

build:
  entrypoint:
    command: "python"
    args: ["-m", "my_custom_mcp_server"]
  push_to_registry: true
  environment_variables:
    OPENAI_API_KEY: "sk-..."
    LOG_LEVEL: "info"

deploy:
  enabled: true
  service_name: "custom-mcp-server"
  gcp:
    allow_unauthenticated: false    # Private service
    max_instances: 50
    cpu_limit: "2000m"              # 2 CPUs for AI workload
    memory_limit: "4Gi"             # 4GB RAM
EOF

mcp-server-automation --provider gcp --config python-gcp.yaml
```

## 🔧 Prerequisites Setup

### AWS Setup
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Configure credentials
aws configure

# Verify setup
aws sts get-caller-identity

# Create ECS cluster (if deploying)
aws ecs create-cluster --cluster-name my-cluster
```

### GCP Setup
```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate and setup
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com

# Verify setup
gcloud config list
```

## 📝 Generated Client Configuration

After deployment, the tool generates MCP client configuration:

```json
{
  "mcpServers": {
    "my-deployed-server": {
      "command": "npx",
      "args": ["-y", "@mcp/server-fetch"],
      "env": {
        "FETCH_MCP_SERVER_URL": "https://your-service-url.com/mcp"
      }
    }
  }
}
```

Copy this configuration to your Claude Desktop config file to use the deployed MCP server.

## 🐛 Troubleshooting

### Missing Dependencies
```bash
❌ AWS provider dependencies not installed.
📦 Installation Options:
  • AWS-only: pip install 'mcp-server-automation[aws]'
  • Multi-cloud: pip install 'mcp-server-automation[all]'
```

### Authentication Issues
```bash
# AWS
aws sts get-caller-identity
aws configure

# GCP
gcloud auth list
gcloud auth login
```

### Docker Permission Errors
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

## 📚 Documentation

- **[INSTALLATION.md](INSTALLATION.md)**: Detailed installation guide with size comparisons
- **[MULTI_CLOUD_README.md](MULTI_CLOUD_README.md)**: Complete multi-cloud documentation
- **Configuration Examples**: See `config-examples/` directory

## 🛡️ Security Best Practices

- Use private subnets for ECS tasks
- Configure proper IAM roles and permissions
- Enable HTTPS with SSL certificates
- Use VPC endpoints for enhanced security
- Regularly update container images

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Install development dependencies: `pip install -e ".[dev]"`
4. Make your changes
5. Run tests: `pytest`
6. Submit a pull request

### Code of Conduct

This project follows both AWS and Google Cloud open source community standards:

- **AWS Projects**: We adopt the [Amazon Open Source Code of Conduct](https://aws.github.io/code-of-conduct). Contact opensource-codeofconduct@amazon.com for questions.
- **Google Cloud Projects**: We follow [Google's Open Source Code of Conduct](https://opensource.google/conduct) promoting inclusive, respectful collaboration. Contact opensource@google.com for concerns.

**Core Principles**: Create inclusive environments, treat all contributors respectfully, encourage constructive collaboration, and address disrespectful behavior promptly.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [mcp-proxy](https://github.com/punkpeye/mcp-proxy) - HTTP transport for MCP servers
- [Model Context Protocol](https://github.com/modelcontextprotocol) - Official MCP specification and servers
- [Claude Desktop](https://claude.ai) - AI assistant that supports MCP servers

---

**Transform your MCP servers into production-ready cloud services with a single command! 🚀**