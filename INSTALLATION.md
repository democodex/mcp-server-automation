# Installation Guide - Optional Dependencies

> **Note:** This package will be published to PyPI soon. For now, install from source.

The MCP Server Automation CLI supports **optional dependency packages** to reduce installation size and complexity. Install only the cloud providers you need!

## 🎯 Installation Options

### Current Installation (From Source)

#### 1. AWS-Only Installation
**Best for:** Users deploying only to AWS ECS
```bash
git clone https://github.com/your-org/mcp-server-automation.git
cd mcp-server-automation
pip install -e ".[aws]"
```
**Includes:** boto3, botocore
**Size:** ~50MB smaller than full installation

#### 2. Google Cloud-Only Installation
**Best for:** Users deploying only to Google Cloud Run
```bash
git clone https://github.com/your-org/mcp-server-automation.git
cd mcp-server-automation
pip install -e ".[gcp]"
```
**Includes:** google-cloud-run, google-cloud-artifact-registry, google-auth, google-cloud-logging
**Size:** ~60MB smaller than full installation

#### 3. Multi-Cloud Installation
**Best for:** Users deploying to both AWS and GCP
```bash
git clone https://github.com/your-org/mcp-server-automation.git
cd mcp-server-automation
pip install -e ".[all]"
```
**Includes:** All AWS and GCP dependencies
**Size:** Full installation with all features

#### 4. Build-Only Installation
**Best for:** Users who only want to build Docker images (no cloud deployment)
```bash
git clone https://github.com/your-org/mcp-server-automation.git
cd mcp-server-automation
pip install -e .
```
**Includes:** Only core dependencies (Docker, Jinja2, YAML)
**Size:** Minimal installation ~20MB

#### 5. Development Installation
**Best for:** Contributors and developers
```bash
git clone https://github.com/your-org/mcp-server-automation.git
cd mcp-server-automation
pip install -e ".[dev]"
```
**Includes:** pytest, black, flake8, mypy for development

### Future Installation (After PyPI Publication)

```bash
# These commands will work once published to PyPI
pip install 'mcp-server-automation[aws]'    # AWS-only
pip install 'mcp-server-automation[gcp]'    # GCP-only
pip install 'mcp-server-automation[all]'    # Multi-cloud
pip install mcp-server-automation           # Base installation
pip install 'mcp-server-automation[dev]'    # Development
```


## 📊 Installation Size Comparison

| Installation Type | Dependencies | Approximate Size | Use Case |
|---|---|---|---|
| Base | Core only | ~20MB | Build-only, no deployment |
| AWS-only | + boto3 | ~35MB | AWS ECS deployment only |
| GCP-only | + Google Cloud libs | ~40MB | Cloud Run deployment only |
| Multi-cloud | + All providers | ~70MB | Deploy to both platforms |
| Development | + Testing tools | ~80MB | Contributing to project |

## 🚀 Usage Examples

### After AWS-Only Installation
```bash
# ✅ Works - AWS deployment
mcp-server-automation --provider aws --config aws-config.yaml

# ❌ Fails - GCP dependencies missing
mcp-server-automation --provider gcp --project-id my-project
# Error: GCP provider dependencies not installed
# Install with: pip install -e ".[gcp]"
```

### After GCP-Only Installation
```bash
# ✅ Works - GCP deployment
mcp-server-automation --provider gcp --project-id my-project --config gcp-config.yaml

# ❌ Fails - AWS dependencies missing
mcp-server-automation --provider aws --config aws-config.yaml
# Error: AWS provider dependencies not installed
# Install with: pip install -e ".[aws]"
```

### After Multi-Cloud Installation
```bash
# ✅ Works - Both providers available
mcp-server-automation --provider aws --config aws-config.yaml
mcp-server-automation --provider gcp --project-id my-project --config gcp-config.yaml
```

## 🔧 Troubleshooting

### Missing Dependencies Error
If you see dependency errors, you can:

1. **Add missing provider:**
   ```bash
   pip install -e ".[gcp]"  # Add GCP support
   ```

2. **Upgrade to multi-cloud:**
   ```bash
   pip install -e ".[all]"  # Get everything
   ```

3. **Reinstall with correct dependencies:**
   ```bash
   pip uninstall mcp-server-automation
   pip install -e ".[aws]"
   ```

### Docker-Only Usage
If you only need Docker building without cloud deployment:
```bash
# Minimal installation
pip install mcp-server-automation

# Build Docker image only (no --push-to-registry)
mcp-server-automation -- npx -y @modelcontextprotocol/server-everything
```

## 🏢 Enterprise/CI-CD Considerations

### Dockerfile Example
```dockerfile
# Multi-cloud CI/CD environment
FROM python:3.11-slim
RUN pip install 'mcp-server-automation[all]'

# AWS-only environment (smaller image)
FROM python:3.11-slim
RUN pip install 'mcp-server-automation[aws]'
```

### GitHub Actions
```yaml
# Install based on deployment target
- name: Install MCP Automation (AWS)
  if: matrix.provider == 'aws'
  run: pip install 'mcp-server-automation[aws]'

- name: Install MCP Automation (GCP)
  if: matrix.provider == 'gcp'
  run: pip install 'mcp-server-automation[gcp]'
```

This optional dependency system reduces installation time, Docker image size, and potential version conflicts while maintaining full backward compatibility! 🎉