# -*- coding: utf-8 -*-
"""Certificate Manager for Certificate Management Service."""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import uuid4

try:
    from .config import Config
except ImportError:
    from config import Config
try:
    from .certificate_generator import CertificateGenerator
    from .certificate_validator import CertificateValidator
except ImportError:
    from certificate_generator import CertificateGenerator
    from certificate_validator import CertificateValidator

logger = logging.getLogger(Config.SERVICE_NAME)


class Certificate:
    """Certificate data model."""

    def __init__(
        self,
        certificate_id: str,
        common_name: str,
        organization: str = "",
        organizational_unit: str = "",
        country: str = "",
        state: str = "",
        locality: str = "",
        email: str = "",
        cert_type: str = "self_signed",
        status: str = "active",
        certificate_pem: str = "",
        private_key_pem: str = "",
        public_key_pem: str = "",
        signature_algorithm: str = "",
        key_algorithm: str = "",
        key_size: int = 0,
        valid_from: Optional[datetime] = None,
        valid_to: Optional[datetime] = None,
        issuer_id: str = "",
        serial_number: str = "",
        tags: Optional[Dict[str, str]] = None,
        created_by: str = "",
    ):
        self.certificate_id = certificate_id
        self.common_name = common_name
        self.organization = organization
        self.organizational_unit = organizational_unit
        self.country = country
        self.state = state
        self.locality = locality
        self.email = email
        self.type = cert_type
        self.status = status
        self.certificate_pem = certificate_pem
        self.private_key_pem = private_key_pem
        self.public_key_pem = public_key_pem
        self.signature_algorithm = signature_algorithm
        self.key_algorithm = key_algorithm
        self.key_size = key_size
        self.valid_from = valid_from or datetime.now(timezone.utc)
        self.valid_to = valid_to or (datetime.now(timezone.utc) + timedelta(days=365))
        self.issuer_id = issuer_id
        self.serial_number = serial_number
        self.tags = tags or {}
        self.created_by = created_by
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.version = 1

    def to_dict(self, include_private_key: bool = False) -> Dict:
        """Convert certificate to dictionary."""
        data = {
            "certificate_id": self.certificate_id,
            "common_name": self.common_name,
            "organization": self.organization,
            "organizational_unit": self.organizational_unit,
            "country": self.country,
            "state": self.state,
            "locality": self.locality,
            "email": self.email,
            "type": self.type,
            "status": self.status,
            "certificate_pem": self.certificate_pem,
            "public_key_pem": self.public_key_pem,
            "signature_algorithm": self.signature_algorithm,
            "key_algorithm": self.key_algorithm,
            "key_size": self.key_size,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "issuer_id": self.issuer_id,
            "serial_number": self.serial_number,
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
        }

        if include_private_key:
            data["private_key_pem"] = self.private_key_pem

        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Certificate":
        """Create certificate from dictionary."""
        return cls(
            certificate_id=data["certificate_id"],
            common_name=data["common_name"],
            organization=data.get("organization", ""),
            organizational_unit=data.get("organizational_unit", ""),
            country=data.get("country", ""),
            state=data.get("state", ""),
            locality=data.get("locality", ""),
            email=data.get("email", ""),
            cert_type=data.get("type", "self_signed"),
            status=data.get("status", "active"),
            certificate_pem=data.get("certificate_pem", ""),
            private_key_pem=data.get("private_key_pem", ""),
            public_key_pem=data.get("public_key_pem", ""),
            signature_algorithm=data.get("signature_algorithm", ""),
            key_algorithm=data.get("key_algorithm", ""),
            key_size=data.get("key_size", 0),
            valid_from=datetime.fromisoformat(data["valid_from"]) if data.get("valid_from") else None,
            valid_to=datetime.fromisoformat(data["valid_to"]) if data.get("valid_to") else None,
            issuer_id=data.get("issuer_id", ""),
            serial_number=data.get("serial_number", ""),
            tags=data.get("tags", {}),
            created_by=data.get("created_by", ""),
        )


class CertificateManager:
    """Manage certificates with storage and lifecycle operations."""

    def __init__(self):
        """Initialize the certificate manager."""
        self.generator = CertificateGenerator()
        self.validator = CertificateValidator()
        self._certificates: Dict[str, Certificate] = {}
        self._revoked_certificates: Dict[str, Dict] = {}
        self._load_from_storage()

    def _load_from_storage(self) -> None:
        """Load certificates from storage."""
        try:
            storage_file = os.path.join(Config.CERTIFICATE_STORAGE_PATH, "certificates.json")
            if os.path.exists(storage_file):
                with open(storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for cert_data in data.get("certificates", []):
                        cert = Certificate.from_dict(cert_data)
                        self._certificates[cert.certificate_id] = cert

                    self._revoked_certificates = data.get("revoked_certificates", {})

                logger.info(f"Loaded {len(self._certificates)} certificates from storage")
        except Exception as e:
            logger.error(f"Failed to load certificates from storage: {e}")

    def _save_to_storage(self) -> None:
        """Save certificates to storage."""
        try:
            os.makedirs(Config.CERTIFICATE_STORAGE_PATH, exist_ok=True)
            storage_file = os.path.join(Config.CERTIFICATE_STORAGE_PATH, "certificates.json")

            data = {
                "certificates": [cert.to_dict(include_private_key=True) for cert in self._certificates.values()],
                "revoked_certificates": self._revoked_certificates,
            }

            with open(storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

            logger.debug("Saved certificates to storage")
        except Exception as e:
            logger.error(f"Failed to save certificates to storage: {e}")

    def create_certificate(
        self,
        common_name: str,
        organization: str = "",
        organizational_unit: str = "",
        country: str = "",
        state: str = "",
        locality: str = "",
        email: str = "",
        cert_type: str = "self_signed",
        validity_days: int = 365,
        key_algorithm: str = "RSA",
        key_size: int = 2048,
        issuer_id: str = "",
        san_dns: Optional[Dict[str, str]] = None,
        san_ip: Optional[List[str]] = None,
        san_email: Optional[List[str]] = None,
        extensions: Optional[Dict[str, str]] = None,
        created_by: str = "",
    ) -> Certificate:
        """
        Create a new certificate.

        Args:
            common_name: Common name (CN)
            organization: Organization (O)
            organizational_unit: Organizational Unit (OU)
            country: Country (C)
            state: State/Province (ST)
            locality: Locality (L)
            email: Email address
            cert_type: Certificate type (self_signed, ca_signed)
            validity_days: Validity period in days
            key_algorithm: Key algorithm (RSA, ECDSA, Ed25519)
            key_size: Key size in bits
            issuer_id: ID of the CA for CA-signed certificates
            san_dns: Subject Alternative Names - DNS
            san_ip: Subject Alternative Names - IP addresses
            san_email: Subject Alternative Names - Email
            extensions: Custom X.509 extensions
            created_by: User or service creating the certificate

        Returns:
            Created Certificate object

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            # Validate parameters
            if cert_type not in Config.CERTIFICATE_TYPES:
                raise ValueError(f"Invalid certificate type: {cert_type}")

            if cert_type == "ca_signed" and not issuer_id:
                raise ValueError("issuer_id is required for CA-signed certificates")

            if validity_days < Config.MIN_VALIDITY_DAYS or validity_days > Config.MAX_VALIDITY_DAYS:
                raise ValueError(
                    f"Validity days must be between {Config.MIN_VALIDITY_DAYS} and {Config.MAX_VALIDITY_DAYS}"
                )

            # Generate key pair
            private_key, public_key = self.generator.generate_key_pair(
                algorithm=key_algorithm,
                key_size=key_size,
            )

            # Serialize keys
            private_key_pem = self.generator.serialize_private_key(private_key)
            public_key_pem = self.generator.serialize_public_key(public_key)

            # Generate certificate
            if cert_type == "self_signed":
                cert_pem, serial_number = self.generator.generate_self_signed_certificate(
                    common_name=common_name,
                    private_key=private_key,
                    public_key=public_key,
                    organization=organization,
                    organizational_unit=organizational_unit,
                    country=country,
                    state=state,
                    locality=locality,
                    email=email,
                    validity_days=validity_days,
                    san_dns=san_dns,
                    san_ip=san_ip,
                    san_email=san_email,
                    extensions=extensions,
                )
            elif cert_type == "ca_signed":
                # Get CA certificate
                ca_cert = self._certificates.get(issuer_id)
                if not ca_cert:
                    raise ValueError(f"CA certificate not found: {issuer_id}")

                if ca_cert.type not in ["root_ca", "intermediate_ca"]:
                    raise ValueError(f"Certificate {issuer_id} is not a CA")

                # Load CA certificate and private key
                ca_cert_obj = self.generator.load_certificate_from_pem(ca_cert.certificate_pem)
                ca_private_key = self.generator.load_private_key_from_pem(ca_cert.private_key_pem)

                cert_pem, serial_number = self.generator.generate_ca_signed_certificate(
                    common_name=common_name,
                    private_key=private_key,
                    public_key=public_key,
                    ca_certificate=ca_cert_obj,
                    ca_private_key=ca_private_key,
                    organization=organization,
                    organizational_unit=organizational_unit,
                    country=country,
                    state=state,
                    locality=locality,
                    email=email,
                    validity_days=validity_days,
                    san_dns=san_dns,
                    san_ip=san_ip,
                    san_email=san_email,
                    extensions=extensions,
                )
            else:
                raise ValueError(f"Unsupported certificate type: {cert_type}")

            # Get certificate info
            cert_info = self.generator.get_certificate_info(cert_pem)

            # Create certificate object
            now = datetime.now(timezone.utc)
            certificate = Certificate(
                certificate_id=str(uuid4()),
                common_name=common_name,
                organization=organization,
                organizational_unit=organizational_unit,
                country=country,
                state=state,
                locality=locality,
                email=email,
                cert_type=cert_type,
                status="active",
                certificate_pem=cert_pem,
                private_key_pem=private_key_pem,
                public_key_pem=public_key_pem,
                signature_algorithm=cert_info.get("signature_algorithm", ""),
                key_algorithm=key_algorithm,
                key_size=key_size,
                valid_from=now,
                valid_to=now + timedelta(days=validity_days),
                issuer_id=issuer_id,
                serial_number=serial_number,
                created_by=created_by,
            )

            # Store certificate
            self._certificates[certificate.certificate_id] = certificate
            self._save_to_storage()

            logger.info(f"Created certificate {certificate.certificate_id} for {common_name}")
            return certificate

        except Exception as e:
            logger.error(f"Failed to create certificate: {e}")
            raise

    def get_certificate(
        self,
        certificate_id: str,
        include_private_key: bool = False,
    ) -> Dict:
        """
        Get a certificate by ID.

        Args:
            certificate_id: Certificate ID
            include_private_key: Whether to include private key

        Returns:
            Dictionary with certificate data

        Raises:
            ValueError: If certificate not found
        """
        cert = self._certificates.get(certificate_id)
        if not cert:
            raise ValueError(f"Certificate not found: {certificate_id}")

        return cert.to_dict(include_private_key=include_private_key)

    def update_certificate(
        self,
        certificate_id: str,
        organization: Optional[str] = None,
        organizational_unit: Optional[str] = None,
        email: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        updated_by: str = "",
    ) -> Certificate:
        """
        Update certificate metadata.

        Args:
            certificate_id: Certificate ID
            organization: New organization
            organizational_unit: New organizational unit
            email: New email
            tags: New tags
            updated_by: User or service updating the certificate

        Returns:
            Updated Certificate object

        Raises:
            ValueError: If certificate not found
        """
        cert = self._certificates.get(certificate_id)
        if not cert:
            raise ValueError(f"Certificate not found: {certificate_id}")

        if organization is not None:
            cert.organization = organization
        if organizational_unit is not None:
            cert.organizational_unit = organizational_unit
        if email is not None:
            cert.email = email
        if tags is not None:
            cert.tags = tags

        cert.updated_at = datetime.now(timezone.utc)
        cert.version += 1

        self._save_to_storage()

        logger.info(f"Updated certificate {certificate_id}")
        return cert

    def delete_certificate(
        self,
        certificate_id: str,
        permanent: bool = False,
    ) -> bool:
        """
        Delete a certificate.

        Args:
            certificate_id: Certificate ID
            permanent: If True, permanently delete; if False, soft delete

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If certificate not found
        """
        cert = self._certificates.get(certificate_id)
        if not cert:
            raise ValueError(f"Certificate not found: {certificate_id}")

        if permanent:
            del self._certificates[certificate_id]
            # Also remove from revoked list if present
            if certificate_id in self._revoked_certificates:
                del self._revoked_certificates[certificate_id]
        else:
            cert.status = "deleted"

        self._save_to_storage()

        logger.info(f"{'Permanently deleted' if permanent else 'Soft deleted'} certificate {certificate_id}")
        return True

    def list_certificates(
        self,
        filter_status: str = "active",
        filter_type: str = "all",
        filter_tag: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """
        List certificates with optional filtering.

        Args:
            filter_status: Filter by status (active, expired, revoked, all)
            filter_type: Filter by type (self_signed, ca_signed, root_ca, intermediate_ca, all)
            filter_tag: Filter by tag key
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of certificate dictionaries
        """
        results = []

        for cert in self._certificates.values():
            # Skip deleted certificates
            if cert.status == "deleted":
                continue

            # Filter by status
            if filter_status != "all" and cert.status != filter_status:
                # Check if expired
                if filter_status == "expired":
                    if cert.valid_to > datetime.now(timezone.utc):
                        continue
                else:
                    if cert.status != filter_status:
                        continue

            # Filter by type
            if filter_type != "all" and cert.type != filter_type:
                continue

            # Filter by tag
            if filter_tag and filter_tag not in cert.tags:
                continue

            results.append(cert.to_dict(include_private_key=False))

        # Apply pagination
        results = results[offset:offset + limit]

        return results

    def renew_certificate(
        self,
        certificate_id: str,
        validity_days: int = 365,
        renewed_by: str = "",
        generate_new_key: bool = False,
    ) -> Certificate:
        """
        Renew an expired or expiring certificate.

        Args:
            certificate_id: Certificate ID
            validity_days: New validity period in days
            renewed_by: User or service renewing the certificate
            generate_new_key: Whether to generate a new key pair

        Returns:
            Renewed Certificate object

        Raises:
            ValueError: If certificate not found
        """
        old_cert = self._certificates.get(certificate_id)
        if not old_cert:
            raise ValueError(f"Certificate not found: {certificate_id}")

        # Determine key algorithm and size
        key_algorithm = old_cert.key_algorithm or Config.DEFAULT_KEY_ALGORITHM
        key_size = old_cert.key_size or Config.DEFAULT_KEY_SIZE

        # Generate new key if requested
        if generate_new_key:
            private_key, public_key = self.generator.generate_key_pair(
                algorithm=key_algorithm,
                key_size=key_size,
            )
        else:
            # Load existing key
            private_key = self.generator.load_private_key_from_pem(old_cert.private_key_pem)
            public_key = self.generator.load_private_key_from_pem(old_cert.private_key_pem).public_key()

        # Serialize keys
        private_key_pem = self.generator.serialize_private_key(private_key)
        public_key_pem = self.generator.serialize_public_key(public_key)

        # Generate new certificate
        if old_cert.type == "self_signed":
            cert_pem, serial_number = self.generator.generate_self_signed_certificate(
                common_name=old_cert.common_name,
                private_key=private_key,
                public_key=public_key,
                organization=old_cert.organization,
                organizational_unit=old_cert.organizational_unit,
                country=old_cert.country,
                state=old_cert.state,
                locality=old_cert.locality,
                email=old_cert.email,
                validity_days=validity_days,
            )
        elif old_cert.type == "ca_signed":
            # Get CA certificate
            ca_cert = self._certificates.get(old_cert.issuer_id)
            if not ca_cert:
                raise ValueError(f"CA certificate not found: {old_cert.issuer_id}")

            # Load CA certificate and private key
            ca_cert_obj = self.generator.load_certificate_from_pem(ca_cert.certificate_pem)
            ca_private_key = self.generator.load_private_key_from_pem(ca_cert.private_key_pem)

            cert_pem, serial_number = self.generator.generate_ca_signed_certificate(
                common_name=old_cert.common_name,
                private_key=private_key,
                public_key=public_key,
                ca_certificate=ca_cert_obj,
                ca_private_key=ca_private_key,
                organization=old_cert.organization,
                organizational_unit=old_cert.organizational_unit,
                country=old_cert.country,
                state=old_cert.state,
                locality=old_cert.locality,
                email=old_cert.email,
                validity_days=validity_days,
            )
        else:
            raise ValueError(f"Unsupported certificate type for renewal: {old_cert.type}")

        # Create new certificate object
        now = datetime.now(timezone.utc)
        new_cert = Certificate(
            certificate_id=str(uuid4()),
            common_name=old_cert.common_name,
            organization=old_cert.organization,
            organizational_unit=old_cert.organizational_unit,
            country=old_cert.country,
            state=old_cert.state,
            locality=old_cert.locality,
            email=old_cert.email,
            cert_type=old_cert.type,
            status="active",
            certificate_pem=cert_pem,
            private_key_pem=private_key_pem,
            public_key_pem=public_key_pem,
            signature_algorithm=old_cert.signature_algorithm,
            key_algorithm=key_algorithm,
            key_size=key_size,
            valid_from=now,
            valid_to=now + timedelta(days=validity_days),
            issuer_id=old_cert.issuer_id,
            serial_number=serial_number,
            tags=old_cert.tags.copy(),
            created_by=renewed_by,
        )

        # Mark old certificate as superseded
        old_cert.status = "superseded"
        old_cert.updated_at = now

        # Store new certificate
        self._certificates[new_cert.certificate_id] = new_cert
        self._save_to_storage()

        logger.info(f"Renewed certificate {certificate_id} -> {new_cert.certificate_id}")
        return new_cert

    def revoke_certificate(
        self,
        certificate_id: str,
        reason: str = "unspecified",
        revoked_by: str = "",
        revocation_date: Optional[datetime] = None,
    ) -> Dict:
        """
        Revoke a certificate.

        Args:
            certificate_id: Certificate ID
            reason: Revocation reason
            revoked_by: User or service revoking the certificate
            revocation_date: Revocation date (default: now)

        Returns:
            Dictionary with revocation status

        Raises:
            ValueError: If certificate not found
        """
        cert = self._certificates.get(certificate_id)
        if not cert:
            raise ValueError(f"Certificate not found: {certificate_id}")

        if cert.status == "revoked":
            return {
                "success": True,
                "message": "Certificate already revoked",
                "revocation_date": self._revoked_certificates.get(certificate_id, {}).get("revocation_date"),
            }

        # Set revocation date
        if revocation_date is None:
            revocation_date = datetime.now(timezone.utc)

        # Update certificate status
        cert.status = "revoked"
        cert.updated_at = revocation_date

        # Add to revoked list
        self._revoked_certificates[certificate_id] = {
            "serial_number": cert.serial_number,
            "revocation_date": revocation_date.isoformat(),
            "reason": reason,
            "revoked_by": revoked_by,
        }

        self._save_to_storage()

        logger.info(f"Revoked certificate {certificate_id} for reason: {reason}")
        return {
            "success": True,
            "message": "Certificate revoked successfully",
            "revocation_date": revocation_date.isoformat(),
        }

    def validate_certificate(
        self,
        certificate_id: str,
        check_expiration: bool = True,
        check_revocation: bool = True,
    ) -> Dict:
        """
        Validate a certificate.

        Args:
            certificate_id: Certificate ID
            check_expiration: Whether to check expiration
            check_revocation: Whether to check revocation

        Returns:
            Dictionary with validation results

        Raises:
            ValueError: If certificate not found
        """
        cert = self._certificates.get(certificate_id)
        if not cert:
            raise ValueError(f"Certificate not found: {certificate_id}")

        # Use validator
        result = self.validator.validate_certificate(
            cert_pem=cert.certificate_pem,
            check_expiration=check_expiration,
            check_revocation=check_revocation,
        )

        # Check if revoked
        if check_revocation and cert.status == "revoked":
            result["valid"] = False
            result["status"] = "revoked"
            result["message"] = "Certificate has been revoked"
            result["validation_errors"].append("Certificate has been revoked")

        return result

    def verify_trust_chain(
        self,
        certificate_id: str,
        trusted_ca_ids: Optional[List[str]] = None,
    ) -> Dict:
        """
        Verify the trust chain of a certificate.

        Args:
            certificate_id: Certificate ID
            trusted_ca_ids: List of trusted CA certificate IDs

        Returns:
            Dictionary with trust chain verification results

        Raises:
            ValueError: If certificate not found
        """
        cert = self._certificates.get(certificate_id)
        if not cert:
            raise ValueError(f"Certificate not found: {certificate_id}")

        # Get trusted CA certificates
        if trusted_ca_ids is None:
            # Use all root CAs as trusted
            trusted_ca_ids = [
                cid for cid, c in self._certificates.items()
                if c.type == "root_ca" and c.status == "active"
            ]

        trusted_ca_certs = []
        for ca_id in trusted_ca_ids:
            ca_cert = self._certificates.get(ca_id)
            if ca_cert and ca_cert.status == "active":
                trusted_ca_certs.append(ca_cert.certificate_pem)

        # Verify trust chain
        result = self.validator.verify_trust_chain(
            cert_pem=cert.certificate_pem,
            trusted_ca_certs=trusted_ca_certs,
        )

        return result

    def get_crl(self, issuer_id: str) -> Dict:
        """
        Get Certificate Revocation List for a CA.

        Args:
            issuer_id: CA certificate ID

        Returns:
            Dictionary with CRL data

        Raises:
            ValueError: If CA not found
        """
        ca_cert = self._certificates.get(issuer_id)
        if not ca_cert:
            raise ValueError(f"CA certificate not found: {issuer_id}")

        if ca_cert.type not in ["root_ca", "intermediate_ca"]:
            raise ValueError(f"Certificate {issuer_id} is not a CA")

        # Collect revoked certificates issued by this CA
        revoked_serials = []
        for cert_id, revocation_info in self._revoked_certificates.items():
            cert = self._certificates.get(cert_id)
            if cert and cert.issuer_id == issuer_id:
                revoked_serials.append((
                    int(cert.serial_number),
                    datetime.fromisoformat(revocation_info["revocation_date"]),
                    revocation_info.get("reason", "unspecified"),
                ))

        # Generate CRL
        now = datetime.now(timezone.utc)
        next_update = now + timedelta(hours=Config.CRL_UPDATE_INTERVAL_HOURS)

        try:
            crl_pem = self.validator.generate_crl(
                ca_cert_pem=ca_cert.certificate_pem,
                ca_private_key_pem=ca_cert.private_key_pem,
                revoked_serials=revoked_serials,
                last_update=now,
                next_update=next_update,
            )

            return {
                "crl_pem": crl_pem,
                "revoked_serial_numbers": [str(s[0]) for s in revoked_serials],
                "last_updated": now.isoformat(),
                "next_update": next_update.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to generate CRL: {e}")
            raise

    def get_expiring_certificates(self, days_threshold: int = 30) -> List[Dict]:
        """
        Get certificates that are expiring soon.

        Args:
            days_threshold: Number of days threshold

        Returns:
            List of certificate dictionaries
        """
        expiring = []
        threshold_date = datetime.now(timezone.utc) + timedelta(days=days_threshold)

        for cert in self._certificates.values():
            if cert.status == "active" and cert.valid_to <= threshold_date:
                expiring.append(cert.to_dict(include_private_key=False))

        return expiring

    def get_certificate_count(self) -> Dict:
        """Get certificate statistics."""
        stats = {
            "total": len(self._certificates),
            "active": 0,
            "expired": 0,
            "revoked": 0,
            "superseded": 0,
            "deleted": 0,
        }

        for cert in self._certificates.values():
            if cert.status in stats:
                stats[cert.status] += 1
            elif cert.valid_to < datetime.now(timezone.utc):
                stats["expired"] += 1

        return stats
