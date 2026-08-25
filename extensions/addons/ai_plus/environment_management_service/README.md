# Environment Management Service

A comprehensive microservice for managing multiple environments (dev, staging, prod) with configuration synchronization, deployment orchestration, and health monitoring.

## Features

- **Multi-Environment Management**: Support for dev, staging, and production environments
- **Configuration Synchronization**: Sync configurations between environments with multiple strategies
- **Deployment Orchestration**: Automated deployment workflows with rollback capabilities
- **Environment Variable Management**: Secure variable storage with secret support
- **Health Checks**: Comprehensive health monitoring for environments
- **Environment Isolation**: Ensures proper isolation between environments
- **Real-time Metrics**: CPU, memory, and connection metrics

## Architecture

```
environment_management_service/
├── main.py                      # Service entry point
├── environment_manager.py      # Core environment management logic
├── config_sync.py              # Configuration synchronization
├── deployment_orchestrator.py   # Deployment orchestration
├── grpc/
│   ├── server.py              # gRPC server implementation
│   ├── client.py              # gRPC client
│   ├── environment_management_pb2.py
│   └── environment_management_pb2_grpc.py
└── proto/
    └── environment_management.proto  # Protocol buffer definitions
```

## Installation

```bash
pip install -r requirements.txt
```

## Running the Service

### Start the server

```bash
python main.py --host [::] --port 50052
```

### Command-line options

- `--host`: Host to bind to (default: `[::]`)
- `--port`: Port to bind to (default: `50052`)
- `--workers`: Maximum number of worker threads (default: `10`)
- `--log-level`: Logging level (default: `INFO`)

## Usage Examples

### Using the gRPC Client

```python
from extensions.addons.ai_plus.environment_management_service.grpc.client import (
    EnvironmentManagementClient,
    EnvironmentManagementClientContext
)

# Using context manager for automatic cleanup
with EnvironmentManagementClientContext(host='localhost', port=50052) as client:
    # List all environments
    result = client.list_environments()
    print(result)
    
    # Create a new environment
    result = client.create_environment(
        name="Test Environment",
        env_type="dev",
        config={"log_level": "DEBUG", "timeout": "30"},
        description="A test environment"
    )
    print(result)
    
    # Get environment details
    env_id = result['environment']['id']
    result = client.get_environment(env_id)
    print(result)
    
    # Set environment variable
    result = client.set_environment_variable(
        environment_id=env_id,
        key="API_KEY",
        value="secret123",
        is_secret=True
    )
    print(result)
    
    # Sync configuration between environments
    result = client.sync_config(
        source_environment_id=source_id,
        target_environment_id=target_id
    )
    print(result)
    
    # Deploy to environment
    result = client.deploy_to_environment(
        source_environment_id=source_id,
        target_environment_id=target_id,
        deployment_type="full"
    )
    print(result)
    
    # Get deployment status
    deployment_id = result['deployment_id']
    result = client.get_deployment_status(deployment_id)
    print(result)
    
    # Health check
    result = client.health_check(env_id)
    print(result)
    
    # Get metrics
    result = client.get_environment_metrics(env_id)
    print(result)
```

### Using the Core Classes Directly

```python
from extensions.addons.ai_plus.environment_management_service import (
    EnvironmentManager,
    ConfigSync,
    DeploymentOrchestrator
)

# Initialize managers
env_manager = EnvironmentManager()
config_sync = ConfigSync(env_manager)
deployment_orchestrator = DeploymentOrchestrator(env_manager, config_sync)

# Create environment
env = env_manager.create_environment(
    name="My Dev Environment",
    env_type="dev",
    config={"log_level": "DEBUG"},
    description="Development environment"
)

# Set variable
env_manager.set_variable(env.id, "DB_HOST", "localhost")

# Sync configuration
result = config_sync.sync_config(
    source_env_id=source_id,
    target_env_id=target_id,
    strategy="merge"
)

# Deploy
deployment = deployment_orchestrator.deploy_to_environment(
    source_env_id=source_id,
    target_env_id=target_id,
    deployment_type="full"
)

# Check deployment status
status = deployment_orchestrator.get_deployment_status(deployment.id)
```

## API Reference

### Environment Management

- `create_environment(name, env_type, config, description)` - Create a new environment
- `get_environment(environment_id)` - Get environment by ID
- `list_environments(env_type, status)` - List environments with filters
- `update_environment(environment_id, config, description)` - Update environment
- `delete_environment(environment_id)` - Delete an environment

### Configuration Management

- `sync_config(source_env_id, target_env_id, config_keys)` - Sync configuration
- `get_config(environment_id)` - Get environment configuration
- `update_config(environment_id, config)` - Update configuration

### Deployment Orchestration

- `deploy_to_environment(source_env_id, target_env_id, deployment_type, parameters)` - Deploy to environment
- `get_deployment_status(deployment_id)` - Get deployment status
- `rollback_deployment(deployment_id, reason)` - Rollback deployment

### Environment Variables

- `set_environment_variable(environment_id, key, value, is_secret)` - Set variable
- `get_environment_variable(environment_id, key)` - Get variable
- `list_environment_variables(environment_id)` - List all variables
- `delete_environment_variable(environment_id, key)` - Delete variable

### Health & Metrics

- `health_check(environment_id)` - Perform health check
- `get_environment_metrics(environment_id)` - Get environment metrics

## Environment Types

- **dev**: Development environment with debug logging and relaxed settings
- **staging**: Staging environment for pre-production testing
- **prod**: Production environment with optimized settings

## Deployment Types

- **full**: Complete deployment with all steps
- **incremental**: Incremental deployment with only changed resources
- **rollback**: Rollback to previous state

## Sync Strategies

- **overwrite**: Overwrite target config with source
- **merge**: Merge configs, source takes precedence
- **selective**: Sync only specified keys

## Data Storage

Environment data is stored in JSON files in the `data/environments/` directory within the service folder.

## Error Handling

The service includes comprehensive error handling for:
- Invalid environment types
- Missing environments
- Invalid deployment transitions
- Configuration sync failures
- Deployment failures

## Testing

Run the test script to verify functionality:

```bash
python test_service.py
```

## License

This service is part of the AI Ops SRE Agent project.
