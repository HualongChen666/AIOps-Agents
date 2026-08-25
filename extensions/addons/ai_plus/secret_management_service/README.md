# Secret Management Service

A comprehensive secret management microservice for AIOps Agent that provides secure storage, encryption, versioning, and access control for sensitive data.

## Features

### Core Functionality
- **Secure Secret Storage**: All secrets are encrypted using AES-256-GCM before storage
- **Secret Versioning**: Track all versions of secrets with ability to revert to previous versions
- **Key Rotation**: Automatic and manual secret rotation with configurable retention periods
- **Access Control**: Fine-grained permission system (read, write, delete, rotate, grant, revoke)
- **Audit Logging**: Comprehensive audit trail of all secret operations
- **Integration**: Seamless integration with core key_management_service

### Security Features
- AES-256-GCM encryption for all secret values
- Encryption key management with rotation support
- File permissions set to 600 (owner read/write only)
- Access control with principal-based permissions
- Comprehensive audit logging for compliance

### API Operations
- `create_secret`: Create a new encrypted secret
- `get_secret`: Retrieve secret metadata and optionally decrypted value
- `update_secret`: Update secret with automatic versioning
- `delete_secret`: Soft or permanent deletion
- `list_secrets`: List secrets with filtering
- `rotate_secret`: Rotate secret to new value
- `get_secret_versions`: Get all versions of a secret
- `revert_secret_version`: Revert to a specific version
- `grant_access`: Grant permissions to a principal
- `revoke_access`: Revoke permissions from a principal
- `list_access`: List all permissions for a secret
- `get_audit_log`: Query audit logs

## Architecture

### Components

1. **main.py**: FastAPI application with REST and RPC endpoints
2. **secret_manager.py**: Core secret management logic with versioning
3. **encryption_service.py**: AES-256-GCM encryption service
4. **access_control.py**: Permission-based access control
5. **audit_log.py**: Comprehensive audit logging
6. **grpc/server.py**: gRPC server for inter-service communication
7. **grpc/client.py**: gRPC client for service communication
8. **config.py**: Configuration management
9. **proto/secret_management.proto**: Protocol Buffer definitions

### Data Flow

```
Client Request → FastAPI → Handler → Secret Manager → Encryption Service → Storage
                                    ↓
                            Access Control Check
                                    ↓
                            Audit Log Entry
```

## Configuration

Environment variables:

- `PORT`: HTTP server port (default: 8005)
- `HOST`: HTTP server host (default: 127.0.0.1)
- `GRPC_PORT`: gRPC server port (default: 50055)
- `GRPC_HOST`: gRPC server host (default: 127.0.0.1)
- `STORAGE_BACKEND`: Storage backend type (default: file)
- `STORAGE_PATH`: Path to storage directory (default: ./secret_storage)
- `ENCRYPTION_ALGORITHM`: Encryption algorithm (default: AES-256-GCM)
- `ENCRYPTION_KEY_PATH`: Path to encryption keys (default: ./encryption_keys)
- `DEFAULT_ROTATION_INTERVAL_DAYS`: Default rotation interval (default: 90)
- `OLD_VALUE_RETENTION_HOURS`: Old value retention (default: 24)
- `MAX_VERSIONS`: Maximum versions to keep (default: 10)
- `ENABLE_ACCESS_CONTROL`: Enable access control (default: true)
- `ENABLE_AUDIT_LOG`: Enable audit logging (default: true)
- `AUDIT_LOG_RETENTION_DAYS`: Audit log retention (default: 90)

## Usage

### Starting the Service

```bash
cd extensions/addons/ai_plus/secret_management_service
pip install -r requirements.txt
python -m secret_management_service.main
```

### Creating a Secret

```python
from secret_management_service.grpc.client import SecretManagementRPCClient

client = SecretManagementRPCClient()
await client.connect()

result = await client.create_secret(
    name="database_password",
    value="my_secure_password",
    description="Production database password",
    created_by="admin",
    tags={"environment": "production", "service": "database"}
)
```

### Retrieving a Secret

```python
# Get metadata only
secret = await client.get_secret(secret_id="xxx", include_value=False)

# Get with decrypted value
secret = await client.get_secret(secret_id="xxx", include_value=True)
```

### Rotating a Secret

```python
result = await client.rotate_secret(
    secret_id="xxx",
    new_value="new_secure_password",
    rotated_by="admin",
    old_value_retention_hours=24
)
```

### Managing Access

```python
# Grant access
await client.grant_access(
    secret_id="xxx",
    principal="service-account-1",
    principal_type="service",
    permissions=["read", "write"],
    granted_by="admin"
)

# Revoke access
await client.revoke_access(
    secret_id="xxx",
    principal="service-account-1",
    revoked_by="admin"
)
```

### Querying Audit Logs

```python
audit_log = await client.get_audit_log(
    secret_id="xxx",
    action="read",
    limit=50
)
```

## Integration with Key Management Service

The service integrates with the core `key_management_service.py` for enhanced key management:

- Secrets are automatically stored in the key management service
- Key rotation uses the key management service's rotation features
- Encryption keys are managed through the key service backend

## Security Considerations

1. **Encryption**: All secrets are encrypted at rest using AES-256-GCM
2. **Key Management**: Encryption keys are stored separately with restricted permissions
3. **Access Control**: Fine-grained permissions prevent unauthorized access
4. **Audit Trail**: All operations are logged for compliance and security monitoring
5. **File Permissions**: Storage files have restricted permissions (600)
6. **Principal Authentication**: Access control checks are performed on all operations

## API Endpoints

### REST Endpoints

- `GET /health`: Health check
- `GET /info`: Service information
- `POST /invoke`: Generic invoke endpoint for all operations
- `POST /rpc/{method}`: RPC endpoint for inter-service communication
- `GET /rpc`: List available RPC methods

### RPC Methods

All operations are available via RPC:
- `create_secret`
- `get_secret`
- `update_secret`
- `delete_secret`
- `list_secrets`
- `rotate_secret`
- `get_secret_versions`
- `revert_secret_version`
- `grant_access`
- `revoke_access`
- `list_access`
- `get_audit_log`
- `health_check`

## Testing

The service includes comprehensive error handling and validation:

- Permission errors are logged and returned as 403 errors
- Not found errors are logged and returned as 404 errors
- All exceptions are caught and logged with full context
- Audit logs track both successful and failed operations

## Monitoring

The service provides:

- Health check endpoint with secret count and audit log count
- Audit log statistics (by action, result, principal)
- Rotation schedule status
- Encryption key status

## Future Enhancements

- Integration with cloud secret managers (AWS Secrets Manager, Azure Key Vault)
- Automatic secret rotation based on policy
- Secret templates and validation
- Multi-region replication
- Advanced authentication (OAuth, JWT)
- Secret sharing with expiration
- Temporary credentials generation
