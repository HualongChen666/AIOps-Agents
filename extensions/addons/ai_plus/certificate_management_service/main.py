# -*- coding: utf-8 -*-
"""Main entry point for Certificate Management Service."""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from .config import Config
    from .certificate_manager import CertificateManager
    from .grpc.server import CertificateManagementRPCServer
except ImportError:
    from config import Config
    from certificate_manager import CertificateManager
    from grpc.server import CertificateManagementRPCServer

# Configure logging
Config.validate()
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format=Config.LOG_FORMAT,
)
logger = logging.getLogger(Config.SERVICE_NAME)

# Initialize FastAPI app
app = FastAPI(title=Config.SERVICE_NAME.replace("_", " ").title())

# Initialize service components
certificate_manager = CertificateManager()
rpc_server = CertificateManagementRPCServer()


# Pydantic models
class GenerateCertificateRequest(BaseModel):
    common_name: str = Field(..., min_length=1, max_length=255)
    organization: str = ""
    organizational_unit: str = ""
    country: str = Field(default="", max_length=2)
    state: str = ""
    locality: str = ""
    email: str = ""
    type: str = Field(default="self_signed", pattern="^(self_signed|ca_signed|root_ca|intermediate_ca)$")
    validity_days: int = Field(default=365, ge=Config.MIN_VALIDITY_DAYS, le=Config.MAX_VALIDITY_DAYS)
    key_algorithm: str = Field(default="RSA", pattern="^(RSA|ECDSA|Ed25519)$")
    key_size: int = Field(default=2048)
    issuer_id: str = ""
    san_dns: Dict[str, str] = Field(default_factory=dict)
    san_ip: List[str] = Field(default_factory=list)
    san_email: List[str] = Field(default_factory=list)
    extensions: Dict[str, str] = Field(default_factory=dict)
    created_by: str = ""


class GetCertificateRequest(BaseModel):
    certificate_id: str = Field(..., min_length=1)
    include_private_key: bool = False
    include_certificate_pem: bool = True


class UpdateCertificateRequest(BaseModel):
    certificate_id: str = Field(..., min_length=1)
    organization: Optional[str] = None
    organizational_unit: Optional[str] = None
    email: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    updated_by: str = ""


class DeleteCertificateRequest(BaseModel):
    certificate_id: str = Field(..., min_length=1)
    permanent: bool = False


class ListCertificatesRequest(BaseModel):
    filter_status: str = "active"
    filter_type: str = "all"
    filter_tag: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class RenewCertificateRequest(BaseModel):
    certificate_id: str = Field(..., min_length=1)
    validity_days: int = Field(default=365, ge=Config.MIN_VALIDITY_DAYS, le=Config.MAX_VALIDITY_DAYS)
    renewed_by: str = ""
    generate_new_key: bool = False


class RevokeCertificateRequest(BaseModel):
    certificate_id: str = Field(..., min_length=1)
    reason: str = Field(default="unspecified")
    revoked_by: str = ""
    revocation_date: int = 0


class ValidateCertificateRequest(BaseModel):
    certificate_id: str = Field(..., min_length=1)
    check_expiration: bool = True
    check_revocation: bool = True
    verify_chain: bool = False


class VerifyTrustChainRequest(BaseModel):
    certificate_id: str = Field(..., min_length=1)
    trusted_ca_ids: List[str] = Field(default_factory=list)


class GetCRLRequest(BaseModel):
    issuer_id: str = Field(..., min_length=1)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = Config.SERVICE_NAME
    certificate_count: int
    revoked_count: int


class InfoResponse(BaseModel):
    service: str
    version: str = "1.0.0"
    status: str = "running"


class InvokeRequest(BaseModel):
    action: str = Field(
        ...,
        pattern="^(generate_certificate|get_certificate|update_certificate|delete_certificate|"
        "list_certificates|renew_certificate|revoke_certificate|validate_certificate|"
        "verify_trust_chain|get_crl|health_check)$"
    )
    payload: Dict[str, Any] = Field(default_factory=dict)


class InvokeResponse(BaseModel):
    success: bool
    service: str
    action: str
    result: Any


# Helper functions
def _generate_certificate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a new certificate."""
    try:
        cert = certificate_manager.create_certificate(
            common_name=payload["common_name"],
            organization=payload.get("organization", ""),
            organizational_unit=payload.get("organizational_unit", ""),
            country=payload.get("country", ""),
            state=payload.get("state", ""),
            locality=payload.get("locality", ""),
            email=payload.get("email", ""),
            cert_type=payload.get("type", "self_signed"),
            validity_days=payload.get("validity_days", Config.DEFAULT_VALIDITY_DAYS),
            key_algorithm=payload.get("key_algorithm", Config.DEFAULT_KEY_ALGORITHM),
            key_size=payload.get("key_size", Config.DEFAULT_KEY_SIZE),
            issuer_id=payload.get("issuer_id", ""),
            san_dns=payload.get("san_dns", {}),
            san_ip=payload.get("san_ip", []),
            san_email=payload.get("san_email", []),
            extensions=payload.get("extensions", {}),
            created_by=payload.get("created_by", ""),
        )

        logger.info(f"Generated certificate {cert.certificate_id} for {cert.common_name}")
        return cert.to_dict(include_private_key=True)

    except ValueError as e:
        logger.error(f"Failed to generate certificate: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_certificate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get a certificate."""
    try:
        return certificate_manager.get_certificate(
            certificate_id=payload["certificate_id"],
            include_private_key=payload.get("include_private_key", False),
        )
    except ValueError as e:
        logger.error(f"Certificate not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _update_certificate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update certificate metadata."""
    try:
        cert = certificate_manager.update_certificate(
            certificate_id=payload["certificate_id"],
            organization=payload.get("organization"),
            organizational_unit=payload.get("organizational_unit"),
            email=payload.get("email"),
            tags=payload.get("tags"),
            updated_by=payload.get("updated_by", ""),
        )

        logger.info(f"Updated certificate {payload['certificate_id']}")
        return cert.to_dict(include_private_key=False)

    except ValueError as e:
        logger.error(f"Failed to update certificate: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _delete_certificate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a certificate."""
    try:
        success = certificate_manager.delete_certificate(
            certificate_id=payload["certificate_id"],
            permanent=payload.get("permanent", False),
        )

        logger.info(f"Deleted certificate {payload['certificate_id']}")
        return {"deleted": payload["certificate_id"], "success": success}

    except ValueError as e:
        logger.error(f"Failed to delete certificate: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _list_certificates(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List certificates."""
    try:
        return certificate_manager.list_certificates(
            filter_status=payload.get("filter_status", "active"),
            filter_type=payload.get("filter_type", "all"),
            filter_tag=payload.get("filter_tag"),
            limit=payload.get("limit", 100),
            offset=payload.get("offset", 0),
        )
    except Exception as e:
        logger.error(f"Failed to list certificates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _renew_certificate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Renew a certificate."""
    try:
        cert = certificate_manager.renew_certificate(
            certificate_id=payload["certificate_id"],
            validity_days=payload.get("validity_days", Config.DEFAULT_VALIDITY_DAYS),
            renewed_by=payload.get("renewed_by", ""),
            generate_new_key=payload.get("generate_new_key", False),
        )

        logger.info(f"Renewed certificate {payload['certificate_id']} -> {cert.certificate_id}")
        return cert.to_dict(include_private_key=True)

    except ValueError as e:
        logger.error(f"Failed to renew certificate: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to renew certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _revoke_certificate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Revoke a certificate."""
    try:
        result = certificate_manager.revoke_certificate(
            certificate_id=payload["certificate_id"],
            reason=payload.get("reason", "unspecified"),
            revoked_by=payload.get("revoked_by", ""),
            revocation_date=datetime.fromtimestamp(payload["revocation_date"]) if payload.get("revocation_date") else None,
        )

        logger.info(f"Revoked certificate {payload['certificate_id']}")
        return result

    except ValueError as e:
        logger.error(f"Failed to revoke certificate: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to revoke certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _validate_certificate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a certificate."""
    try:
        return certificate_manager.validate_certificate(
            certificate_id=payload["certificate_id"],
            check_expiration=payload.get("check_expiration", True),
            check_revocation=payload.get("check_revocation", True),
        )
    except ValueError as e:
        logger.error(f"Failed to validate certificate: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to validate certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _verify_trust_chain(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Verify trust chain."""
    try:
        return certificate_manager.verify_trust_chain(
            certificate_id=payload["certificate_id"],
            trusted_ca_ids=payload.get("trusted_ca_ids"),
        )
    except ValueError as e:
        logger.error(f"Failed to verify trust chain: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to verify trust chain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_crl(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get Certificate Revocation List."""
    try:
        return certificate_manager.get_crl(issuer_id=payload["issuer_id"])
    except ValueError as e:
        logger.error(f"Failed to get CRL: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get CRL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _health_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Health check."""
    stats = certificate_manager.get_certificate_count()
    return {
        "healthy": True,
        "status": "ok",
        "version": "1.0.0",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "certificate_count": stats["total"],
        "revoked_count": stats["revoked"],
    }


# Register handlers
HANDLERS = {
    "generate_certificate": _generate_certificate,
    "get_certificate": _get_certificate,
    "update_certificate": _update_certificate,
    "delete_certificate": _delete_certificate,
    "list_certificates": _list_certificates,
    "renew_certificate": _renew_certificate,
    "revoke_certificate": _revoke_certificate,
    "validate_certificate": _validate_certificate,
    "verify_trust_chain": _verify_trust_chain,
    "get_crl": _get_crl,
    "health_check": _health_check,
}

# Register RPC handlers
for name, handler in HANDLERS.items():
    rpc_server.register(name, handler)


# FastAPI endpoints
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    stats = certificate_manager.get_certificate_count()
    return HealthResponse(
        status="ok",
        service=Config.SERVICE_NAME,
        certificate_count=stats["total"],
        revoked_count=stats["revoked"],
    )


@app.get("/info", response_model=InfoResponse)
async def info() -> InfoResponse:
    """Service info endpoint."""
    return InfoResponse(service=Config.SERVICE_NAME)


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(req: InvokeRequest) -> InvokeResponse:
    """Generic invoke endpoint for all actions."""
    handler = HANDLERS.get(req.action)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")

    try:
        result = handler(req.payload)
        return InvokeResponse(
            success=True, service=Config.SERVICE_NAME, action=req.action, result=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invoke failed for action {req.action}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rpc/{method}")
async def rpc_call(method: str, payload: Dict[str, Any] = None):
    """RPC endpoint for inter-service communication."""
    try:
        result = await rpc_server.call(method, payload or {})
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"RPC call {method} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rpc")
async def list_rpc_methods():
    """List available RPC methods."""
    return {"methods": rpc_server.list_methods()}


# Lifecycle events
@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info(f"Starting {Config.SERVICE_NAME}")
    await rpc_server.start(Config.GRPC_HOST, Config.GRPC_PORT)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info(f"Shutting down {Config.SERVICE_NAME}")
    await rpc_server.stop()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        log_level=Config.LOG_LEVEL.lower(),
    )
