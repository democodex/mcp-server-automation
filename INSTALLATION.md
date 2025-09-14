# Installation Guide - Optional Dependencies

The MCP Server Automation CLI supports **optional dependency packages** to reduce installation size and complexity. Install only the cloud providers you need!

## 🎯 Installation Options

### 1. AWS-Only Installation
**Best for:** Users deploying only to AWS ECS
```bash
pip install 'mcp-server-automation[aws]'
```
**Includes:** boto3, botocore
**Size:** ~50MB smaller than full installation

### 2. Google Cloud-Only Installation
**Best for:** Users deploying only to Google Cloud Run
```bash
pip install 'mcp-server-automation[gcp]'
```
**Includes:** google-cloud-run, google-cloud-artifact-registry, google-auth, google-cloud-logging
**Size:** ~60MB smaller than full installation

### 3. Multi-Cloud Installation
**Best for:** Users deploying to both AWS and GCP
```bash
pip install 'mcp-server-automation[all]'
```
**Includes:** All AWS and GCP dependencies
**Size:** Full installation with all features

### 4. Build-Only Installation
**Best for:** Users who only want to build Docker images (no cloud deployment)
```bash
pip install mcp-server-automation
```
**Includes:** Only core dependencies (Docker, Jinja2, YAML)
**Size:** Minimal installation ~20MB

### 5. Development Installation
**Best for:** Contributors and developers
```bash
pip install 'mcp-server-automation[dev]'
```
**Includes:** pytest, black, flake8, mypy for development

### 6. Legacy Installation (Backward Compatibility)
**Best for:** Existing users with AWS-only workflows
```bash
pip install 'mcp-server-automation[legacy]'
```
**Includes:** boto3, botocore (same as [aws])
**Note:** Maintains original behavior

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
# Install with: pip install 'mcp-server-automation[gcp]'
```

### After GCP-Only Installation
```bash
# ✅ Works - GCP deployment
mcp-server-automation --provider gcp --project-id my-project --config gcp-config.yaml

# ❌ Fails - AWS dependencies missing
mcp-server-automation --provider aws --config aws-config.yaml
# Error: AWS provider dependencies not installed
# Install with: pip install 'mcp-server-automation[aws]'
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
   pip install 'mcp-server-automation[gcp]'  # Add GCP support
   ```

2. **Upgrade to multi-cloud:**
   ```bash
   pip install 'mcp-server-automation[all]'  # Get everything
   ```

3. **Reinstall with correct dependencies:**
   ```bash
   pip uninstall mcp-server-automation
   pip install 'mcp-server-automation[aws]'
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