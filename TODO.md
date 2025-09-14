# Cloud-Agnostic Refactoring Plan
**Multi-Cloud Support: AWS ECS + Google Cloud Run**

## 🏗️ Architecture Abstraction Strategy

### 1. Cloud Provider Interface Pattern
Create abstract base classes for all cloud-specific operations:

```python
# New file: mcp_server_automation/cloud/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class CloudProvider(ABC):
    @abstractmethod
    def deploy_container_service(self, config: 'DeployConfig') -> str

    @abstractmethod
    def push_container_image(self, image_tag: str, config: 'BuildConfig') -> str

    @abstractmethod
    def get_service_url(self, service_name: str) -> str
```

### 2. Provider-Specific Implementations
- **AWS Provider:** `cloud/aws_provider.py` (existing logic)
- **GCP Provider:** `cloud/gcp_provider.py` (new implementation)

---

## 📋 Service Mapping: AWS → Google Cloud

| **AWS Service** | **Google Cloud Equivalent** | **Abstraction Required** |
|---|---|---|
| **ECR** (Container Registry) | **Artifact Registry** | Container image push/pull operations |
| **ECS Fargate** (Serverless containers) | **Cloud Run** | Serverless container deployment |
| **Application Load Balancer** | **Cloud Load Balancing** | HTTP/HTTPS traffic routing |
| **CloudFormation** | **Deployment Manager / Terraform** | Infrastructure as Code |
| **VPC/Subnets** | **VPC/Subnets** | Network configuration |
| **Security Groups** | **Firewall Rules** | Network access control |
| **IAM Roles** | **Service Accounts** | Identity and access management |
| **CloudWatch Logs** | **Cloud Logging** | Log aggregation |
| **Route53** (optional) | **Cloud DNS** | DNS management |

---

## 🔧 Refactoring Implementation Strategy

### Phase 1: Core Abstraction Layer

#### 1.1 Create Provider Factory
```python
# New file: mcp_server_automation/cloud/factory.py
class CloudProviderFactory:
    @staticmethod
    def create_provider(provider_type: str) -> CloudProvider:
        if provider_type.lower() == 'aws':
            return AWSProvider()
        elif provider_type.lower() == 'gcp':
            return GCPProvider()
        else:
            raise ValueError(f"Unsupported provider: {provider_type}")
```

#### 1.2 Refactor Configuration System
```python
# Updated: mcp_server_automation/config.py
@dataclass
class CloudConfig:
    provider: str  # 'aws' or 'gcp'
    region: str
    project_id: Optional[str] = None  # GCP only
    account_id: Optional[str] = None  # AWS only

@dataclass
class ContainerRegistryConfig:
    provider: str
    registry_url: Optional[str] = None  # Auto-generated if None
    repository_name: str = "mcp-servers"
```

#### 1.3 Abstract Container Operations
```python
# New file: mcp_server_automation/cloud/container_ops.py
class ContainerRegistryOperations(ABC):
    @abstractmethod
    def build_registry_url(self) -> str

    @abstractmethod
    def authenticate(self) -> None

    @abstractmethod
    def push_image(self, image_tag: str) -> str

    @abstractmethod
    def create_repository_if_needed(self, repo_name: str) -> None
```

### Phase 2: AWS Provider Implementation
Move existing AWS logic into provider-specific classes:

#### 2.1 AWS Provider Structure
```
mcp_server_automation/cloud/aws/
├── __init__.py
├── provider.py          # Main AWSProvider class
├── ecr_handler.py       # ECR operations (from docker_handler.py)
├── ecs_deployer.py      # ECS deployment (from deploy.py)
├── cloudformation.py    # CF template management
└── templates/
    └── ecs-service.yaml # Existing template
```

#### 2.2 Extract AWS-specific Logic
- Move `docker_handler.py` ECR methods → `aws/ecr_handler.py`
- Move `deploy.py` CloudFormation logic → `aws/ecs_deployer.py`
- Keep existing functionality identical for backward compatibility

### Phase 3: Google Cloud Provider Implementation

#### 3.1 GCP Provider Structure
```
mcp_server_automation/cloud/gcp/
├── __init__.py
├── provider.py          # Main GCPProvider class
├── artifact_registry.py # Container registry operations
├── cloud_run_deployer.py # Cloud Run deployment
├── gcp_auth.py         # Authentication handling
└── templates/
    └── cloud-run-service.yaml # Cloud Run YAML template
```

#### 3.2 GCP Service Implementations

**Google Artifact Registry Handler:**
```python
# cloud/gcp/artifact_registry.py
from google.cloud import artifactregistry_v1
from google.auth import default

class ArtifactRegistryHandler:
    def __init__(self, project_id: str, location: str):
        self.project_id = project_id
        self.location = location
        self.client = artifactregistry_v1.ArtifactRegistryClient()

    def create_repository_if_needed(self, repo_name: str):
        # Similar to ECR repository creation

    def get_registry_url(self) -> str:
        return f"{self.location}-docker.pkg.dev/{self.project_id}"
```

**Cloud Run Deployment Handler:**
```python
# cloud/gcp/cloud_run_deployer.py
from google.cloud import run_v2

class CloudRunDeployer:
    def deploy_service(self, config: 'DeployConfig') -> str:
        # Deploy container to Cloud Run
        # Handle traffic allocation, authentication, etc.

    def create_load_balancer(self, service_url: str) -> str:
        # Optional: Create Cloud Load Balancer for custom domains
```

### Phase 4: Configuration Schema Updates

#### 4.1 Multi-Cloud Configuration Format
```yaml
# New unified configuration format
cloud:
  provider: "aws"  # or "gcp"
  region: "us-east-1"  # AWS region or GCP region/zone
  project_id: "my-gcp-project"  # GCP only

build:
  # Existing structure remains the same
  entrypoint:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-everything"]
  push_to_registry: true  # Renamed from push_to_ecr

deploy:
  enabled: true
  service_name: "mcp-everything-server"

  # Cloud-specific sections
  aws:
    cluster_name: "mcp-cluster"
    vpc_id: "vpc-12345678"
    alb_subnet_ids: ["subnet-1", "subnet-2"]
    ecs_subnet_ids: ["subnet-3"]
    certificate_arn: "arn:aws:acm:..."

  gcp:
    allow_unauthenticated: true  # Public Cloud Run service
    max_instances: 10
    cpu_limit: "1000m"
    memory_limit: "512Mi"
    custom_domain: "myservice.example.com"  # Optional
```

---

## 🔄 Implementation Steps

### Step 1: Create Abstraction Foundation
1. **Create cloud provider interfaces** (`cloud/base.py`)
2. **Create provider factory** (`cloud/factory.py`)
3. **Update configuration system** to support multi-cloud
4. **Create cloud-agnostic CLI** with `--provider` flag

### Step 2: Refactor Existing AWS Code
1. **Move AWS logic** to `cloud/aws/` directory structure
2. **Wrap existing functions** in AWSProvider class
3. **Maintain backward compatibility** with current CLI usage
4. **Update imports** throughout codebase

### Step 3: Implement GCP Provider
1. **Install GCP dependencies**: `google-cloud-run`, `google-cloud-artifact-registry`
2. **Implement GCPProvider** with Cloud Run deployment logic
3. **Create Cloud Run YAML templates** (equivalent to CloudFormation)
4. **Add GCP authentication** handling

### Step 4: Update Build System
1. **Refactor docker_handler.py** to use cloud provider abstractions
2. **Support both ECR and Artifact Registry** push operations
3. **Update Docker image tagging** for different registry formats
4. **Maintain existing direct command mode** functionality

### Step 5: Update CLI Interface
```bash
# AWS deployment (existing)
mcp-server-automation --config config.yaml

# GCP deployment (new)
mcp-server-automation --provider gcp --config config.yaml

# Provider-specific direct commands
mcp-server-automation --provider gcp --push-to-registry -- npx -y @modelcontextprotocol/server-everything
```

---

## 📚 Required Dependencies

### New GCP Dependencies
```python
# pyproject.toml additions
dependencies = [
    # Existing AWS dependencies
    "boto3>=1.26.0",

    # New GCP dependencies
    "google-cloud-run>=0.9.0",
    "google-cloud-artifact-registry>=1.9.0",
    "google-auth>=2.0.0",
    "google-cloud-logging>=3.0.0",
]
```

### Optional Dependencies
```python
[project.optional-dependencies]
aws = ["boto3>=1.26.0"]
gcp = [
    "google-cloud-run>=0.9.0",
    "google-cloud-artifact-registry>=1.9.0",
    "google-auth>=2.0.0",
    "google-cloud-logging>=3.0.0",
]
```

---

## 🔧 File Structure After Refactoring

```
mcp_server_automation/
├── __init__.py
├── __main__.py
├── cli.py                    # Updated with --provider flag
├── config.py                 # Multi-cloud configuration
├── build.py                  # Cloud-agnostic build orchestration
├── mcp_config.py            # Updated for both ALB and Cloud Run URLs
├── utils.py                 # Unchanged
├── package_detector.py      # Unchanged
├── command_parser.py        # Unchanged
├── github_handler.py        # Unchanged
├── dockerfile_generator.py  # Unchanged
├── cloud/
│   ├── __init__.py
│   ├── base.py              # Abstract interfaces
│   ├── factory.py           # Provider factory
│   ├── aws/
│   │   ├── __init__.py
│   │   ├── provider.py      # AWSProvider implementation
│   │   ├── ecr_handler.py   # ECR operations (from docker_handler.py)
│   │   ├── ecs_deployer.py  # ECS deployment (from deploy.py)
│   │   └── templates/
│   │       └── ecs-service.yaml
│   └── gcp/
│       ├── __init__.py
│       ├── provider.py      # GCPProvider implementation
│       ├── artifact_registry.py # Artifact Registry operations
│       ├── cloud_run_deployer.py # Cloud Run deployment
│       └── templates/
│           └── cloud-run-service.yaml
└── templates/
    ├── Dockerfile-nodejs.j2  # Unchanged
    └── Dockerfile-python.j2  # Unchanged
```

---

## 📖 Migration Guide

### Backward Compatibility
- **Existing AWS configurations** continue to work unchanged
- **CLI commands** remain identical for AWS deployments
- **Configuration file format** supports both old and new schemas

### New GCP Usage Examples
```bash
# Build and deploy to Cloud Run
mcp-server-automation --provider gcp --config gcp-config.yaml

# Direct command to Cloud Run
mcp-server-automation --provider gcp --push-to-registry -- uvx mcp-server-automation

# Build for specific GCP region
mcp-server-automation --provider gcp --region us-central1 -- python -m myserver
```

### Configuration Migration
```yaml
# Old AWS-only format (still supported)
build:
  push_to_ecr: true
  aws_region: "us-east-1"

# New multi-cloud format
cloud:
  provider: "gcp"
  region: "us-central1"
  project_id: "my-project"

build:
  push_to_registry: true  # Works for both ECR and Artifact Registry
```

---

## 🧪 Testing Strategy

### Integration Tests
1. **Mock both AWS and GCP clients** for unit testing
2. **Test provider factory** with different configurations
3. **Test configuration parsing** for both cloud providers
4. **Test backward compatibility** with existing AWS configs

### E2E Testing
1. **AWS E2E tests** using existing infrastructure
2. **GCP E2E tests** using Google Cloud Run
3. **Cross-cloud deployment** validation
4. **Direct command mode** testing for both providers

---

## 🎯 Implementation Priority

### High Priority (Core Multi-Cloud Support)
1. Abstract interfaces and provider factory
2. AWS provider refactoring (maintain existing functionality)
3. Basic GCP Cloud Run deployment
4. Updated CLI with `--provider` flag
5. Multi-cloud configuration support

### Medium Priority (Enhanced Features)
1. GCP custom domain support
2. Cloud Load Balancer integration
3. Advanced Cloud Run configuration (CPU/memory limits)
4. GCP-specific error handling and validation

### Low Priority (Advanced Features)
1. Hybrid cloud deployments
2. Cloud cost optimization features
3. Multi-region deployments
4. Advanced networking configurations

---

## 📋 Success Criteria

✅ **Backward Compatibility:** Existing AWS deployments continue to work unchanged

✅ **Feature Parity:** GCP deployments provide equivalent functionality to AWS ECS

✅ **Configuration Simplicity:** Single configuration file supports both providers

✅ **CLI Consistency:** Same command patterns work for both AWS and GCP

✅ **Error Handling:** Clear, provider-specific error messages and remediation

---

## 📝 Implementation Notes

This refactoring plan transforms the AWS-specific MCP automation tool into a truly multi-cloud platform while maintaining all existing functionality and providing a clear migration path for users.

Key design principles:
- **Abstraction over duplication:** Common interfaces for cloud operations
- **Backward compatibility:** Existing AWS workflows unchanged
- **Provider isolation:** Clean separation of cloud-specific logic
- **Configuration flexibility:** Support both old and new config formats
- **Extensibility:** Easy to add additional cloud providers in the future