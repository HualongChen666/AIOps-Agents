# Release Management Service

A comprehensive microservice for managing software releases, versioning, builds, and deployments.

## Features

### Version Management
- Semantic versioning (SemVer) support
- Automatic version increment (major, minor, patch)
- Pre-release version support (alpha, beta, rc)
- Build metadata support
- Version comparison and diff calculation

### Release Management
- Create and manage releases
- Release workflow management (draft → pending → approved → deployed)
- Change tracking and release notes
- Multi-environment support (dev, staging, production)
- Release history and audit trail

### Build Management
- Docker image building
- Package archive creation (tar.gz, zip)
- Binary compilation
- Build artifact management
- Build timeout and error handling
- Checksum calculation for artifact integrity

### Deployment Management
- Docker container deployment
- Package deployment to hosts
- Multi-host deployment support
- Deployment status tracking
- Automatic rollback on failure
- Deployment history

### Approval Workflow
- Configurable approval requirements
- Multi-approver support
- Approval comments and audit trail
- Auto-approval for development environments

## Architecture

```
release_management_service/
├── main.py                 # Service entry point and API endpoints
├── config.py              # Configuration settings
├── version_manager.py     # Semantic versioning management
├── release_builder.py     # Build and artifact management
├── deployment_manager.py  # Deployment and rollback management
├── grpc/
│   ├── server.py         # gRPC server implementation
│   └── client.py         # gRPC client for inter-service communication
└── proto/
    └── release_management.proto  # gRPC service definition
```

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Service Info
- `GET /info` - Service information

### Generic Invoke
- `POST /invoke` - Generic endpoint for all actions

### RPC Methods
- `POST /rpc/{method}` - Call specific RPC method
- `GET /rpc` - List available RPC methods

## Available Actions

### Release Management
- `create_release` - Create a new release
- `get_release` - Get release by ID
- `list_releases` - List all releases with filters
- `update_release` - Update release information
- `delete_release` - Delete a release
- `get_release_history` - Get release event history
- `get_release_status` - Get detailed release status

### Build Management
- `build_release` - Build a release package

### Deployment Management
- `deploy_release` - Deploy a release to environment
- `rollback_release` - Rollback to previous version

### Approval Management
- `approve_release` - Approve a release
- `reject_release` - Reject a release

### Version Management
- `create_version` - Create a new version
- `get_version` - Get version information
- `list_versions` - List versions for a project
- `increment_version` - Increment a version
- `compare_versions` - Compare two versions

## Configuration

Environment variables:

- `PORT` - HTTP server port (default: 8003)
- `HOST` - HTTP server host (default: 127.0.0.1)
- `GRPC_PORT` - gRPC server port (default: 50053)
- `GRPC_HOST` - gRPC server host (default: 127.0.0.1)
- `RELEASES_DIR` - Directory for release data (default: ./releases)
- `ARTIFACTS_DIR` - Directory for build artifacts (default: ./artifacts)
- `BUILD_DIR` - Directory for build files (default: ./build)
- `BUILD_TIMEOUT` - Build timeout in seconds (default: 3600)
- `DEPLOYMENT_TIMEOUT` - Deployment timeout in seconds (default: 1800)
- `AUTO_APPROVE_DEV` - Auto-approve for dev environment (default: true)
- `LOG_LEVEL` - Logging level (default: INFO)

## Usage Examples

### Create a Release

```python
import requests

response = requests.post("http://localhost:8003/invoke", json={
    "action": "create_release",
    "payload": {
        "project_name": "my-app",
        "release_type": "minor",
        "description": "New feature release",
        "changes": ["Added user authentication", "Fixed bug #123"],
        "environment": "staging",
        "requires_approval": True,
        "approvers": ["devops-team", "tech-lead"]
    }
})
```

### Build a Release

```python
response = requests.post("http://localhost:8003/invoke", json={
    "action": "build_release",
    "payload": {
        "release_id": "release-id-here",
        "build_type": "docker",
        "build_args": {
            "ENV": "production",
            "DEBUG": "false"
        },
        "dockerfile_path": "./Dockerfile"
    }
})
```

### Deploy a Release

```python
response = requests.post("http://localhost:8003/invoke", json={
    "action": "deploy_release",
    "payload": {
        "release_id": "release-id-here",
        "target_environment": "production",
        "target_hosts": ["host1.example.com", "host2.example.com"],
        "deployment_config": {
            "ports": "80:80,443:443",
            "environment": {
                "ENV": "production"
            },
            "restart_policy": "unless-stopped"
        },
        "rollback_on_failure": True
    }
})
```

### Approve a Release

```python
response = requests.post("http://localhost:8003/invoke", json={
    "action": "approve_release",
    "payload": {
        "release_id": "release-id-here",
        "approver": "tech-lead",
        "comment": "Approved for production deployment"
    }
})
```

### Rollback a Release

```python
response = requests.post("http://localhost:8003/invoke", json={
    "action": "rollback_release",
    "payload": {
        "release_id": "release-id-here",
        "rollback_to_version": "1.2.3",
        "reason": "Critical bug discovered",
        "force": False
    }
})
```

### Version Management

```python
# Create a new version
response = requests.post("http://localhost:8003/invoke", json={
    "action": "create_version",
    "payload": {
        "project_name": "my-app",
        "increment_type": "minor",
        "pre_release": "beta",
        "pre_release_number": 1
    }
})

# Compare versions
response = requests.post("http://localhost:8003/invoke", json={
    "action": "compare_versions",
    "payload": {
        "version1": "2.0.0",
        "version2": "1.9.9"
    }
})
```

## Running the Service

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python -m release_management_service.main

# Or with uvicorn directly
uvicorn release_management_service.main:app --host 127.0.0.1 --port 8003
```

## gRPC Client Usage

```python
from release_management_service.grpc import create_client

async def main():
    client = await create_client(host="127.0.0.1", port=50053)

    # Create a release
    release = await client.create_release(
        project_name="my-app",
        release_type="minor",
        description="New feature release"
    )

    # Build the release
    build = await client.build_release(
        release_id=release["id"],
        build_type="docker"
    )

    # Deploy the release
    deployment = await client.deploy_release(
        release_id=release["id"],
        target_environment="production",
        target_hosts=["host1.example.com"]
    )

    await client.close()
```

## Release Workflow

1. **Create Release** - Initialize a new release with version and metadata
2. **Request Approval** - If approval is required, send to approvers
3. **Approve Release** - Approvers review and approve the release
4. **Build Release** - Build the release package (Docker image, package, or binary)
5. **Deploy Release** - Deploy to target environment
6. **Monitor** - Track deployment status and health
7. **Rollback** - If needed, rollback to previous version

## Error Handling

The service includes comprehensive error handling for:
- Invalid version strings
- Build failures and timeouts
- Deployment failures
- Missing artifacts
- Approval workflow violations
- Configuration validation errors

## Storage

The service uses in-memory storage for:
- Release records
- Version history
- Build information
- Deployment records
- Release events

For production use, consider integrating with a persistent database (PostgreSQL, MongoDB, etc.) and object storage (S3, GCS) for artifacts.
