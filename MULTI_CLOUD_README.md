# Multi-Cloud MCP Server Automation

**✨ NEW: Multi-Cloud Support for AWS ECS and Google Cloud Run**

The MCP Server Automation CLI now supports deployment to both AWS ECS and Google Cloud Run, providing a unified interface for containerizing and deploying MCP servers across multiple cloud platforms.

## 🚀 Quick Start - Multi-Cloud

### AWS ECS Deployment
```bash
# Using new multi-cloud CLI
mcp-server-automation --provider aws --push-to-registry --config aws-config.yaml

# Direct command mode
mcp-server-automation --provider aws --push-to-registry -- npx -y @modelcontextprotocol/server-everything
```

### Google Cloud Run Deployment
```bash
# Using configuration file
mcp-server-automation --provider gcp --config gcp-config.yaml

# Direct command mode
mcp-server-automation --provider gcp --project-id my-project --push-to-registry -- uvx mcp-server
```

## 📋 Multi-Cloud Configuration Format

The new configuration format supports both AWS and GCP deployments with cloud-specific sections:

```yaml
# Multi-cloud configuration example
cloud:
  provider: "gcp"  # or "aws"
  region: "us-central1"
  project_id: "my-gcp-project"  # Required for GCP

build:
  entrypoint:
    command: "uvx"
    args: ["mcp-server-automation"]
  push_to_registry: true  # Renamed from push_to_ecr
  environment_variables:
    LOG_LEVEL: "info"

deploy:
  enabled: true
  service_name: "mcp-automation-server"

  # Cloud-specific deployment configuration
  aws:
    cluster_name: "mcp-cluster"
    vpc_id: "vpc-12345678"
    alb_subnet_ids: ["subnet-1", "subnet-2"]
    ecs_subnet_ids: ["subnet-3"]
    certificate_arn: "arn:aws:acm:..."  # Optional HTTPS

  gcp:
    allow_unauthenticated: true  # Public access
    max_instances: 10
    cpu_limit: "1000m"          # 1 CPU core
    memory_limit: "1Gi"         # 1 GB RAM
    custom_domain: "mcp.example.com"  # Optional

  save_config: "./mcp-config.json"
```

## 🔄 Migration from Legacy Format

### Backward Compatibility
- **Existing AWS configurations continue to work unchanged**
- **Legacy CLI commands remain functional**
- **No breaking changes to current workflows**

### Automatic CLI Selection
The tool automatically chooses the appropriate CLI:
- **Multi-cloud CLI**: When `--provider` flag is used
- **Legacy CLI**: For existing AWS-only configurations
- **Environment variable**: Set `MCP_USE_MULTI_CLOUD=true` to force new CLI

### Migration Examples

**Old AWS-only format:**
```yaml
build:
  push_to_ecr: true
  aws_region: "us-east-1"
deploy:
  cluster_name: "mcp-cluster"
  # ... other AWS settings
```

**New multi-cloud format:**
```yaml
cloud:
  provider: "aws"
  region: "us-east-1"
build:
  push_to_registry: true  # Renamed
deploy:
  enabled: true
  aws:
    cluster_name: "mcp-cluster"
    # ... other AWS settings
```

## 🔧 Installation

### Base Installation
```bash
pip install mcp-server-automation
```

### Provider-Specific Dependencies
```bash
# For AWS support
pip install "mcp-server-automation[aws]"

# For GCP support
pip install "mcp-server-automation[gcp]"

# For both providers
pip install "mcp-server-automation[all]"
```

## 🏗️ Architecture

### Cloud Provider Abstraction
- **CloudProvider Interface**: Unified API for all cloud operations
- **Provider Factory**: Automatic provider instantiation and validation
- **Registry Operations**: Abstracted container registry operations (ECR vs Artifact Registry)
- **Deployment Operations**: Abstracted deployment operations (ECS vs Cloud Run)

### Service Mapping

| **AWS Service** | **Google Cloud Equivalent** | **Abstraction** |
|---|---|---|
| **ECR** | **Artifact Registry** | Container Registry Operations |
| **ECS Fargate** | **Cloud Run** | Deployment Operations |
| **Application Load Balancer** | **Cloud Load Balancing** | HTTP/HTTPS endpoints |
| **CloudFormation** | **gcloud CLI** | Infrastructure deployment |
| **VPC/Security Groups** | **VPC/Firewall Rules** | Network configuration |

## 📚 Usage Examples

### Configuration Files

**AWS ECS Example** (`aws-config.yaml`):
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
    alb_subnet_ids: ["subnet-pub-1", "subnet-pub-2"]
    ecs_subnet_ids: ["subnet-priv-1"]
    certificate_arn: "arn:aws:acm:us-east-1:123456789012:certificate/abc123"
```

**Google Cloud Run Example** (`gcp-config.yaml`):
```yaml
cloud:
  provider: "gcp"
  region: "us-central1"
  project_id: "my-project-id"

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
    cpu_limit: "2000m"
    memory_limit: "2Gi"
    ingress: "all"
```

### CLI Usage Examples

```bash
# AWS deployment with configuration file
mcp-server-automation --provider aws --config aws-config.yaml

# GCP deployment with configuration file
mcp-server-automation --provider gcp --config gcp-config.yaml

# AWS direct command mode
mcp-server-automation --provider aws --push-to-registry -- npx -y @modelcontextprotocol/server-everything

# GCP direct command mode with specific region
mcp-server-automation --provider gcp --region europe-west1 --project-id my-project -- python -m server

# Multi-architecture builds
mcp-server-automation --provider aws --arch linux/arm64 --push-to-registry -- uvx mcp-server

# Build only (no deployment)
mcp-server-automation --provider gcp --project-id my-project -- python -m server
```

## 🧪 Prerequisites

### AWS Prerequisites
- **AWS CLI** configured with appropriate permissions
- **Docker** with BuildKit support
- **AWS ECR repository** (auto-created if needed)
- **AWS ECS cluster** (specified in configuration)

### GCP Prerequisites
- **Google Cloud CLI (gcloud)** installed and configured
- **Docker** with BuildKit support
- **GCP project** with required APIs enabled:
  - Cloud Run API
  - Artifact Registry API
  - Cloud Build API (optional)

## 🔐 Required Permissions

### AWS Permissions
- ECR: `ecr:*` (repository and image operations)
- ECS: `ecs:*` (service and task management)
- CloudFormation: `cloudformation:*` (stack operations)
- IAM: `iam:CreateRole`, `iam:AttachRolePolicy`, `iam:PassRole`
- EC2: VPC and subnet access
- Elastic Load Balancing: ALB operations

### GCP Permissions
- **Cloud Run Admin** role or equivalent permissions:
  - `run.services.create`
  - `run.services.update`
  - `run.services.setIamPolicy`
- **Artifact Registry Admin** role or equivalent permissions:
  - `artifactregistry.repositories.create`
  - `artifactregistry.repositories.uploadArtifacts`
- **Project Editor** or custom role for infrastructure operations

## 🐛 Troubleshooting

### Provider Dependencies
```bash
# Check if provider dependencies are installed
mcp-server-automation --provider aws --help  # Should not error
mcp-server-automation --provider gcp --help  # Should not error
```

### Authentication Issues

**AWS:**
```bash
aws sts get-caller-identity  # Check AWS credentials
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ecr-uri>
```

**GCP:**
```bash
gcloud auth list  # Check GCP authentication
gcloud config set project PROJECT_ID
gcloud auth configure-docker REGION-docker.pkg.dev
```

### Common Error Resolution

**AWS "Repository not found":**
- ECR repository is auto-created, check IAM permissions
- Verify region and account ID

**GCP "Permission denied":**
- Run `gcloud auth login` to re-authenticate
- Check project ID and enabled APIs
- Verify Artifact Registry and Cloud Run permissions

**Docker build failures:**
- Ensure Docker daemon is running
- Check Dockerfile syntax and base images
- Verify network connectivity for package downloads

## 🆕 What's New

### v1.1.0 - Multi-Cloud Support
- ✅ **Google Cloud Run support** with complete feature parity
- ✅ **Multi-cloud configuration format** with backward compatibility
- ✅ **Provider-specific CLI flags** (`--provider`, `--project-id`)
- ✅ **Automatic dependency validation** and installation guidance
- ✅ **Cloud-agnostic build system** supporting both registries
- ✅ **Enhanced error handling** with provider-specific guidance
- ✅ **Optional dependency packages** for targeted installation

### Legacy Support
- ✅ **Full backward compatibility** with existing AWS workflows
- ✅ **Automatic CLI selection** based on usage patterns
- ✅ **Legacy configuration support** with migration warnings
- ✅ **Unchanged CLI behavior** for existing users

This multi-cloud implementation transforms the tool from an AWS-only solution into a truly portable, cloud-agnostic platform for MCP server deployment while maintaining complete backward compatibility.