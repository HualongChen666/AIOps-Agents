# Access Control Service

A comprehensive access control microservice that implements both Role-Based Access Control (RBAC) and Attribute-Based Access Control (ABAC) for the AIOps platform.

## Features

### RBAC (Role-Based Access Control)
- **Permission Management**: Create, update, delete, and list permissions
- **Role Management**: Create, update, delete, and list roles with permission assignments
- **Role Assignment**: Assign and revoke roles from subjects (users/services)
- **Permission Inheritance**: Support for role hierarchy and inherited permissions
- **Effective Permissions**: Calculate all effective permissions for a subject including inherited ones

### ABAC (Attribute-Based Access Control)
- **Policy Management**: Create, update, delete, and list ABAC policies
- **Complex Conditions**: Support for subject, resource, and environment conditions
- **Policy Priority**: Execute policies based on priority
- **Policy Effects**: Support for allow and deny effects
- **Dynamic Evaluation**: Real-time policy evaluation based on attributes

### Combined Access Control
- **Hybrid Model**: Combines RBAC and ABAC for flexible access control
- **RBAC First**: Checks RBAC permissions first for performance
- **ABAC Fallback**: Falls back to ABAC if RBAC doesn't grant access
- **Unified API**: Single interface for both access control models

### Audit & Compliance
- **Access Logging**: Log all access decisions for audit trails
- **Decision Tracking**: Track which policies/roles granted access
- **Filterable Logs**: Query audit logs by subject, resource, time range
- **Statistics**: Get access control statistics and metrics

## Architecture

```
access_control_service/
├── main.py                      # Service main entry point (FastAPI)
├── access_control_manager.py    # Core access control logic
├── policy_enforcer.py           # Policy enforcement and audit logging
├── permission_checker.py        # Permission checking utilities
├── grpc/
│   ├── __init__.py
│   ├── server.py                # gRPC server implementation
│   └── client.py                # gRPC client implementation
├── test_basic.py                # Basic tests
└── README.md                    # This file
```

## Components

### AccessControlManager
Main manager that coordinates RBAC and ABAC:
- Initializes and manages RBAC and ABAC engines
- Provides unified access control interface
- Handles combined RBAC+ABAC decision making
- Delegates to appropriate managers based on operation

### RBACManager
Handles role-based access control:
- Manages permissions (CRUD operations)
- Manages roles (CRUD operations)
- Manages subject-role assignments
- Calculates effective permissions with inheritance
- Checks permissions based on role assignments

### PolicyEnforcer
Enforces access control policies:
- Evaluates access requests using combined RBAC+ABAC
- Logs all access decisions for audit
- Provides audit log querying
- Generates access control statistics

### PermissionChecker
Provides simplified permission checking:
- Simple permission check API
- Batch permission checking
- Permission enumeration for subjects
- Role hierarchy resolution
- Effective role calculation

## API Endpoints

### Permission Management
- `POST /permissions` - Create a new permission
- `GET /permissions/{permission_id}` - Get a permission
- `PUT /permissions/{permission_id}` - Update a permission
- `DELETE /permissions/{permission_id}` - Delete a permission
- `GET /permissions` - List permissions

### Role Management
- `POST /roles` - Create a new role
- `GET /roles/{role_id}` - Get a role
- `PUT /roles/{role_id}` - Update a role
- `DELETE /roles/{role_id}` - Delete a role
- `GET /roles` - List roles
- `POST /roles/assign` - Assign a role to a subject
- `POST /roles/revoke` - Revoke a role from a subject
- `GET /subjects/{subject_id}/roles` - Get subject roles

### Policy Management (ABAC)
- `POST /policies` - Create a new ABAC policy
- `GET /policies/{policy_id}` - Get a policy
- `PUT /policies/{policy_id}` - Update a policy
- `DELETE /policies/{policy_id}` - Delete a policy
- `GET /policies` - List policies

### Access Control
- `POST /check` - Check access permission

### Audit Logging
- `GET /audit` - Get audit logs

### Permission Checker
- `GET /subjects/{subject_id}/permissions` - Get subject permissions
- `GET /subjects/{subject_id}/roles/effective` - Get effective roles

## gRPC Service

The service also provides a gRPC interface defined in `proto/access_control.proto`:

### Service: AccessControlService
- Permission management RPCs
- Role management RPCs
- Policy management RPCs
- Access control RPCs
- Audit logging RPCs
- Health check RPC

## Configuration

Environment variables:
- `PORT` - HTTP server port (default: 8001)
- `GRPC_PORT` - gRPC server port (default: 50054)
- `HOST` - Server host (default: 127.0.0.1)

## Dependencies

- FastAPI - HTTP API framework
- grpcio - gRPC framework
- PostgreSQL - Database for persistence
- loguru - Logging

## Integration

The service integrates with:
- `core.rbac` - Basic RBAC utilities
- `core.abac` - ABAC engine implementation
- `core.storage.postgres_storage` - PostgreSQL storage

## Usage Example

### Create a Permission
```python
POST /permissions
{
    "name": "read_anomalies",
    "description": "Read anomaly data",
    "resource_type": "anomaly",
    "actions": ["read"]
}
```

### Create a Role
```python
POST /roles
{
    "name": "anomaly_reader",
    "description": "Can read anomaly data",
    "permission_ids": ["1"],
    "inherited_role_ids": []
}
```

### Assign Role to User
```python
POST /roles/assign
{
    "subject_id": "user123",
    "role_id": "1"
}
```

### Check Permission
```python
POST /check
{
    "subject_id": "user123",
    "subject_type": "user",
    "resource_id": "anomaly456",
    "resource_type": "anomaly",
    "action": "read"
}
```

### Create ABAC Policy
```python
POST /policies
{
    "name": "owner_access",
    "description": "Allow owners full access",
    "effect": "allow",
    "subject_conditions": {},
    "resource_conditions": {
        "owner": {"equals": "user123"}
    },
    "environment_conditions": {},
    "actions": ["read", "write", "delete"],
    "priority": 10
}
```

## Running the Service

### HTTP Server Only
```bash
python main.py
```

### With Custom Configuration
```bash
PORT=8080 GRPC_PORT=50055 python main.py
```

## Testing

Run basic tests:
```bash
python test_basic.py
```

## Security Considerations

- All access decisions are logged for audit
- Default deny policy if no matching rules found
- RBAC checked first for performance
- ABAC provides fine-grained control
- Policy priority prevents conflicts
- Support for both allow and deny effects

## Future Enhancements

- Cache frequently used permissions
- Add policy validation
- Support for time-based policies
- Integration with external identity providers
- Policy versioning and rollback
- Advanced audit reporting
- Real-time permission updates
