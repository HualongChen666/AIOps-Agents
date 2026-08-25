# Identity Management Service

A comprehensive microservice for user lifecycle management, authentication, and identity operations.

## Features

### User Lifecycle Management
- **Create Users**: Create new users with password hashing
- **Update Users**: Update user information (email, name, role, etc.)
- **Delete Users**: Safely delete users from the system
- **List Users**: List users with filtering capabilities
- **Disable Users**: Temporarily disable user accounts

### User Attributes Management
- **Custom Attributes**: Store custom key-value attributes for users
- **Attribute CRUD**: Create, read, update, delete user attributes

### Multi-Factor Authentication (MFA)
- **TOTP Support**: Time-based One-Time Password authentication
- **Recovery Codes**: Generate and manage recovery codes
- **MFA Enable/Disable**: Enable or disable MFA per user
- **MFA Verification**: Verify MFA codes during login

### Single Sign-On (SSO) Integration
- **SSO Provider Configuration**: Configure external SSO providers
- **SSO Login**: Authenticate users via SSO
- **Token Management**: Handle SSO tokens and JWT generation

### User Group Management
- **Create Groups**: Create user groups for role-based access
- **Update Groups**: Modify group membership and attributes
- **Delete Groups**: Remove groups from the system
- **Group Membership**: Add/remove users from groups
- **List Groups**: List all groups with pagination

### User Provisioning
- **Automated Provisioning**: Automated user setup with groups and attributes
- **Bulk Provisioning**: Create multiple users at once
- **Deprovisioning**: Safe user deactivation and cleanup
- **External Sync**: Sync users from external sources (LDAP, AD)

## Architecture

### Components

1. **main.py**: FastAPI application with REST endpoints
2. **identity_manager.py**: Core identity management logic
3. **user_provisioning.py**: Automated user lifecycle operations
4. **authentication_provider.py**: Authentication and SSO integration
5. **group_manager.py**: User group management
6. **grpc/server.py**: gRPC server implementation
7. **grpc/client.py**: gRPC/HTTP client for service communication

### Integration

The service integrates with:
- **core/auth_service.py**: Password hashing, JWT token generation
- **core/user_service.py**: User database operations
- **core/auth_db.py**: Database models and sessions

## API Endpoints

### Health & Info
- `GET /health` - Health check
- `GET /` - Service information

### User Management
- `POST /users` - Create a new user
- `GET /users/{username}` - Get user by username
- `PUT /users/{username}` - Update user
- `DELETE /users/{username}` - Delete user
- `GET /users` - List users (with filters)

### User Attributes
- `POST /users/{username}/attributes` - Set user attribute
- `DELETE /users/{username}/attributes/{key}` - Delete user attribute

### MFA
- `POST /users/{username}/mfa/enable` - Enable MFA
- `POST /users/{username}/mfa/disable` - Disable MFA
- `POST /users/{username}/mfa/verify` - Verify MFA code

### Groups
- `POST /groups` - Create group
- `GET /groups/{group_id}` - Get group
- `PUT /groups/{group_id}` - Update group
- `DELETE /groups/{group_id}` - Delete group
- `GET /groups` - List groups
- `POST /groups/members` - Add user to group
- `DELETE /groups/members` - Remove user from group

### SSO
- `POST /sso/configure` - Configure SSO provider
- `POST /sso/login` - SSO login

### Authentication
- `POST /auth/login` - User login
- `POST /auth/mfa` - MFA login

### Provisioning
- `POST /provision` - Provision user
- `POST /deprovision/{username}` - Deprovision user

## Configuration

Environment variables:
- `PORT`: HTTP server port (default: 8000)
- `GRPC_PORT`: gRPC server port (default: 50053)
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `JWT_ACCESS_EXPIRE_MINUTES`: Token expiration time (default: 30)
- `MFA_ISSUER`: MFA issuer name (default: "AIOps Identity Management")
- `SSO_ENABLED`: Enable SSO features (default: false)

## Running the Service

### HTTP Server
```bash
cd extensions/addons/ai_plus/identity_management_service
python main.py
```

### gRPC Server
```bash
cd extensions/addons/ai_plus/identity_management_service/grpc
python server.py
```

## Usage Examples

### Create a User
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post("http://localhost:8000/users", json={
        "username": "john_doe",
        "password": "secure_password",
        "email": "john@example.com",
        "full_name": "John Doe",
        "role": "user"
    })
    user = response.json()
```

### Enable MFA
```python
response = await client.post("http://localhost:8000/users/john_doe/mfa/enable")
mfa_config = response.json()
# Returns: {"secret": "...", "recovery_codes": [...], "enabled": true}
```

### Create a Group
```python
response = await client.post("http://localhost:8000/groups", json={
    "name": "developers",
    "description": "Developer team",
    "usernames": ["john_doe", "jane_doe"]
})
group = response.json()
```

## gRPC Interface

The service defines a gRPC interface in `proto/identity_management.proto` with the following services:

- `CreateUser`
- `UpdateUser`
- `DeleteUser`
- `GetUser`
- `ListUsers`
- `SetUserAttribute`
- `DeleteUserAttribute`
- `EnableMFA`
- `DisableMFA`
- `VerifyMFA`
- `CreateUserGroup`
- `UpdateUserGroup`
- `DeleteUserGroup`
- `GetUserGroup`
- `ListUserGroups`
- `AddUserToGroup`
- `RemoveUserFromGroup`
- `ConfigureSSO`
- `SSOLogin`
- `HealthCheck`

## Dependencies

- FastAPI
- SQLAlchemy
- PyJWT
- passlib
- bcrypt
- pyotp
- httpx
- grpcio

## Security Considerations

- Passwords are hashed using bcrypt
- JWT tokens are signed with a configurable secret key
- MFA secrets are stored securely in the database
- SSO tokens are validated with external providers
- All sensitive operations require proper authentication

## Error Handling

The service returns appropriate HTTP status codes:
- `200 OK`: Successful operation
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Testing

Run tests with:
```bash
pytest extensions/addons/ai_plus/identity_management_service/tests/
```

## License

This service is part of the AIOps SRE Agent project.
