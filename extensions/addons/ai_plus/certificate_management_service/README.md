# Certificate Management Service

A microservice for managing X.509 certificates with full lifecycle support including generation, validation, renewal, and revocation.

## Features

- **Certificate Generation**
  - Self-signed certificates
  - CA-signed certificates
  - Root CA and intermediate CA certificates
  - Support for RSA, ECDSA, and Ed25519 key algorithms
  - Subject Alternative Names (SAN) support
  - Custom X.509 extensions

- **Certificate Storage**
  - Persistent storage in JSON format
  - Secure private key storage
  - Certificate metadata management
  - Tag-based organization

- **Certificate Validation**
  - Expiration checking
  - Signature verification
  - Basic constraints validation
  - Key usage validation
  - Trust chain verification

- **Certificate Lifecycle**
  - Certificate renewal with optional key regeneration
  - Certificate revocation with CRL support
  - Soft delete and permanent delete
  - Status tracking (active, expired, revoked, superseded)

- **Certificate Revocation List (CRL)**
  - Automatic CRL generation
  - Configurable update intervals
  - Multiple revocation reasons

## Architecture

```
certificate_management_service/
├── main.py                      # Service entry point with FastAPI
├── config.py                    # Configuration management
├── certificate_manager.py       # Certificate storage and lifecycle
├── certificate_generator.py    # Certificate generation logic
├── certificate_validator.py    # Certificate validation logic
├── grpc/
│   ├── client.py               # gRPC client
│   ├── server.py               # gRPC server
│   └── __init__.py
├── proto/
│   └── certificate_management.proto  # gRPC service definition
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## API Endpoints

### REST API

- `GET /health` - Health check
- `GET /info` - Service information
- `POST /invoke` - Generic invoke endpoint
- `POST /rpc/{method}` - RPC endpoint
- `GET /rpc` - List available RPC methods

### Supported Actions

- `generate_certificate` - Generate a new certificate
- `get_certificate` - Get certificate by ID
- `update_certificate` - Update certificate metadata
- `delete_certificate` - Delete a certificate
- `list_certificates` - List certificates with filters
- `renew_certificate` - Renew an expiring certificate
- `revoke_certificate` - Revoke a certificate
- `validate_certificate` - Validate a certificate
- `verify_trust_chain` - Verify certificate trust chain
- `get_crl` - Get Certificate Revocation List
- `health_check` - Health check

## Configuration

Environment variables:

- `CMS_HOST` - Server host (default: 0.0.0.0)
- `CMS_PORT` - Server port (default: 8003)
- `CMS_GRPC_HOST` - gRPC host (default: 0.0.0.0)
- `CMS_GRPC_PORT` - gRPC port (default: 50053)
- `CMS_LOG_LEVEL` - Log level (default: INFO)
- `CMS_CERTIFICATE_STORAGE_PATH` - Storage path (default: data/certificates)
- `CMS_DEFAULT_VALIDITY_DAYS` - Default validity (default: 365)
- `CMS_DEFAULT_KEY_ALGORITHM` - Default key algorithm (default: RSA)
- `CMS_DEFAULT_KEY_SIZE` - Default key size (default: 2048)

## Usage Examples

### Generate a Self-Signed Certificate

```python
from certificate_management_service.grpc.client import CertificateManagementRPCClient

client = CertificateManagementRPCClient()
await client.connect()

result = await client.generate_certificate(
    common_name="example.com",
    organization="My Company",
    country="US",
    validity_days=365,
    key_algorithm="RSA",
    key_size=2048,
    san_dns={"www.example.com": "example.com"},
    created_by="admin"
)

print(result)
```

### Generate a CA-Signed Certificate

```python
# First, create a root CA
root_ca = await client.generate_certificate(
    common_name="My Root CA",
    organization="My Company",
    type="root_ca",
    validity_days=3650,
    created_by="admin"
)

# Then, create a certificate signed by the CA
cert = await client.generate_certificate(
    common_name="example.com",
    organization="My Company",
    type="ca_signed",
    issuer_id=root_ca["certificate_id"],
    validity_days=365,
    created_by="admin"
)
```

### Validate a Certificate

```python
result = await client.validate_certificate(
    certificate_id="cert-id",
    check_expiration=True,
    check_revocation=True
)

if result["valid"]:
    print("Certificate is valid")
else:
    print(f"Certificate invalid: {result['message']}")
```

### Renew a Certificate

```python
result = await client.renew_certificate(
    certificate_id="cert-id",
    validity_days=365,
    renewed_by="admin",
    generate_new_key=True
)
```

### Revoke a Certificate

```python
result = await client.revoke_certificate(
    certificate_id="cert-id",
    reason="key_compromise",
    revoked_by="admin"
)
```

### Get Certificate Revocation List

```python
crl = await client.get_crl(issuer_id="ca-id")
print(f"CRL contains {len(crl['revoked_serial_numbers'])} revoked certificates")
```

## Security Considerations

- Private keys are stored in the certificate storage file
- In production, consider using a secure key management system
- Use appropriate key sizes (RSA 2048+, ECDSA 256+)
- Implement proper access controls
- Enable certificate expiration monitoring
- Regularly update CRLs

## Dependencies

- FastAPI - Web framework
- Uvicorn - ASGI server
- Pydantic - Data validation
- Cryptography - X.509 certificate operations

## Running the Service

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python -m certificate_management_service.main
```

Or using uvicorn directly:

```bash
uvicorn certificate_management_service.main:app --host 0.0.0.0 --port 8003
```

## Testing

The service includes real cryptographic operations using the `cryptography` library. All certificate generation, signing, and validation operations are performed with actual X.509 certificates.

## License

This service is part of the AI Plus extensions package.
