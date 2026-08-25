# Dependency Management Service

A microservice for managing Python project dependencies, including scanning, version checking, security vulnerability detection, and dependency updates.

## Features

- **Dependency Scanning**: Scan Python projects for dependencies from multiple sources (requirements.txt, pyproject.toml, setup.py, Pipfile)
- **Version Checking**: Check for outdated packages using PyPI API
- **Security Vulnerability Detection**: Detect security vulnerabilities in dependencies
- **Dependency Updates**: Update dependencies using pip, poetry, or pipenv
- **Conflict Detection**: Detect and report dependency conflicts
- **Lock File Generation**: Generate lock files for reproducible builds
- **Dependency Tree**: View dependency trees for packages

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Configuration is handled via environment variables:

- `PORT`: HTTP server port (default: 8003)
- `HOST`: HTTP server host (default: 127.0.0.1)
- `GRPC_PORT`: gRPC server port (default: 50053)
- `GRPC_HOST`: gRPC server host (default: 127.0.0.1)
- `SCAN_TIMEOUT`: Scan timeout in seconds (default: 300)
- `MAX_CONCURRENT_SCANS`: Maximum concurrent scans (default: 4)
- `CACHE_DURATION`: Cache duration in seconds (default: 3600)
- `PYPI_API_URL`: PyPI API URL (default: https://pypi.org/pypi)
- `CHECK_TIMEOUT`: Version check timeout in seconds (default: 60)
- `UPDATE_TIMEOUT`: Update timeout in seconds (default: 600)
- `BACKUP_BEFORE_UPDATE`: Create backup before update (default: true)
- `AUTO_RESOLVE_CONFLICTS`: Auto-resolve conflicts (default: false)
- `LOCK_FILE_DIR`: Lock file directory (default: ./locks)
- `LOG_LEVEL`: Logging level (default: INFO)

## Usage

### Starting the Service

```bash
python -m dependency_management_service.main
```

Or using uvicorn:

```bash
uvicorn dependency_management_service.main:app --host 127.0.0.1 --port 8003
```

### API Endpoints

#### Health Check

```bash
GET /health
```

#### Service Info

```bash
GET /info
```

#### Generic Invoke

```bash
POST /invoke
{
  "action": "scan_dependencies",
  "payload": {
    "project_path": "/path/to/project",
    "scan_types": ["requirements.txt", "pyproject.toml"]
  }
}
```

#### RPC Call

```bash
POST /rpc/{method}
{
  "project_path": "/path/to/project"
}
```

#### List RPC Methods

```bash
GET /rpc
```

### Available Actions

1. **scan_dependencies**: Scan project for dependencies
2. **check_outdated**: Check for outdated packages
3. **check_vulnerabilities**: Check for security vulnerabilities
4. **update_dependencies**: Update dependencies
5. **detect_conflicts**: Detect dependency conflicts
6. **generate_lock_file**: Generate lock file
7. **get_dependency_tree**: Get dependency tree for a package
8. **resolve_dependencies**: Resolve dependencies

### Example Usage

#### Scan Dependencies

```python
from dependency_management_service.grpc import SyncDependencyManagementRPCClient

client = SyncDependencyManagementRPCClient(host="127.0.0.1", port=8003)

result = client.scan_dependencies(
    project_path="/path/to/project",
    scan_types=["requirements.txt", "pyproject.toml"]
)

print(result)
```

#### Check for Outdated Packages

```python
result = client.check_outdated(
    project_path="/path/to/project",
    package_names=["requests", "numpy"]
)

print(result)
```

#### Check for Vulnerabilities

```python
result = client.check_vulnerabilities(
    project_path="/path/to/project",
    severity_level="high"
)

print(result)
```

#### Update Dependencies

```python
result = client.update_dependencies(
    project_path="/path/to/project",
    package_names=["requests"],
    update_type="specific",
    dry_run=True
)

print(result)
```

#### Detect Conflicts

```python
result = client.detect_conflicts(
    project_path="/path/to/project"
)

print(result)
```

#### Generate Lock File

```python
result = client.generate_lock_file(
    project_path="/path/to/project",
    lock_file_type="requirements.lock"
)

print(result)
```

#### Get Dependency Tree

```python
result = client.get_dependency_tree(
    project_path="/path/to/project",
    package_name="requests",
    depth=3
)

print(result)
```

## Architecture

### Components

- **main.py**: FastAPI application and HTTP endpoints
- **dependency_scanner.py**: Scans projects for dependencies
- **version_checker.py**: Checks versions and vulnerabilities
- **update_manager.py**: Manages dependency updates
- **grpc/server.py**: RPC server implementation
- **grpc/client.py**: RPC client implementation
- **config.py**: Configuration management

### Data Flow

1. Client sends request via HTTP or RPC
2. Request is routed to appropriate handler
3. Handler calls relevant service component
4. Service component performs operation
5. Result is returned to client

## Supported Package Managers

- pip (requirements.txt)
- Poetry (pyproject.toml, poetry.lock)
- Pipenv (Pipfile, Pipfile.lock)
- setuptools (setup.py)

## Error Handling

The service includes comprehensive error handling:

- File not found errors
- Invalid project paths
- Network errors (PyPI API)
- Package manager errors
- Timeout handling
- Backup and restore on failure

## Logging

The service uses Python's logging module with configurable log levels:

- DEBUG: Detailed debugging information
- INFO: General informational messages
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical error messages

## gRPC Protocol

The service defines a gRPC protocol in `proto/dependency_management.proto`. This can be used to generate gRPC client/server code for other languages.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

The service follows PEP 8 style guidelines.

## License

This service is part of the AI Plus extension suite.
