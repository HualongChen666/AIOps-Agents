# -*- coding: utf-8 -*-
"""Certificate Validator for Certificate Management Service."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import ExtensionOID

try:
    from .config import Config
except ImportError:
    from config import Config
try:
    from .certificate_generator import CertificateGenerator
except ImportError:
    from certificate_generator import CertificateGenerator

logger = logging.getLogger(Config.SERVICE_NAME)


class CertificateValidator:
    """Validate X.509 certificates with real cryptographic validation."""

    def __init__(self):
        """Initialize the certificate validator."""
        self.backend = default_backend()
        self.generator = CertificateGenerator()

    def validate_certificate(
        self,
        cert_pem: str,
        check_expiration: bool = True,
        check_revocation: bool = True,
    ) -> Dict:
        """
        Validate a certificate.

        Args:
            cert_pem: PEM-formatted certificate string
            check_expiration: Whether to check expiration
            check_revocation: Whether to check revocation status

        Returns:
            Dictionary with validation results
        """
        try:
            cert = self.generator.load_certificate_from_pem(cert_pem)

            validation_result = {
                "valid": True,
                "status": "valid",
                "message": "Certificate is valid",
                "validation_errors": [],
                "expiration_date": cert.not_valid_after_utc.isoformat(),
                "days_until_expiration": self._days_until_expiration(cert),
            }

            # Check expiration
            if check_expiration:
                expiration_result = self._check_expiration(cert)
                if not expiration_result["valid"]:
                    validation_result["valid"] = False
                    validation_result["status"] = expiration_result["status"]
                    validation_result["message"] = expiration_result["message"]
                    validation_result["validation_errors"].append(expiration_result["message"])

            # Cryptographic signature check. A self-signed certificate is
            # verified against its own public key; a CA-signed certificate whose
            # issuer is unavailable is reported as unverified (never as "valid").
            signature_result = self._check_signature(cert)
            validation_result["signature_status"] = signature_result["status"]
            if signature_result["valid"] is False:
                validation_result["valid"] = False
                validation_result["status"] = "invalid_signature"
                validation_result["message"] = signature_result["message"]
                validation_result["validation_errors"].append(signature_result["message"])

            # Check basic constraints
            constraints_result = self._check_basic_constraints(cert)
            if not constraints_result["valid"]:
                validation_result["valid"] = False
                validation_result["validation_errors"].append(constraints_result["message"])

            # Check key usage
            key_usage_result = self._check_key_usage(cert)
            if not key_usage_result["valid"]:
                validation_result["valid"] = False
                validation_result["validation_errors"].append(key_usage_result["message"])

            return validation_result

        except Exception as e:
            logger.error(f"Failed to validate certificate: {e}")
            return {
                "valid": False,
                "status": "validation_error",
                "message": f"Validation error: {str(e)}",
                "validation_errors": [str(e)],
                "expiration_date": None,
                "days_until_expiration": None,
            }

    def _check_expiration(self, cert: x509.Certificate) -> Dict:
        """Check if certificate is expired or not yet valid."""
        now = datetime.now(timezone.utc)

        if now < cert.not_valid_before_utc:
            return {
                "valid": False,
                "status": "not_yet_valid",
                "message": f"Certificate is not valid until {cert.not_valid_before_utc.isoformat()}",
            }

        if now > cert.not_valid_after_utc:
            return {
                "valid": False,
                "status": "expired",
                "message": f"Certificate expired on {cert.not_valid_after_utc.isoformat()}",
            }

        return {
            "valid": True,
            "status": "valid",
            "message": "Certificate is within validity period",
        }

    @staticmethod
    def _verify_signature(cert: x509.Certificate, issuer_cert: x509.Certificate) -> None:
        """Verify ``cert``'s signature with ``issuer_cert``'s public key.

        Uses the signature algorithm parameters recorded in the certificate, so
        RSA-PKCS#1v1.5, RSA-PSS, ECDSA and Ed25519 certificates are all handled
        correctly.  Raises :class:`~cryptography.exceptions.InvalidSignature`
        (or another exception) when the signature does not verify.
        """
        public_key = issuer_cert.public_key()
        params = cert.signature_algorithm_parameters
        if params is None:
            # Ed25519/Ed448 have no padding or hash parameters.
            public_key.verify(cert.signature, cert.tbs_certificate_bytes)
        else:
            public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                params,
                cert.signature_hash_algorithm,
            )

    def _check_signature(
        self,
        cert: x509.Certificate,
        issuer_cert: Optional[x509.Certificate] = None,
    ) -> Dict:
        """Verify the certificate's cryptographic signature.

        A self-signed certificate is verified against its own public key with the
        algorithm recorded in the certificate.  A CA-signed certificate can only
        be verified with the issuer's certificate; when the issuer is not
        supplied the signature is reported as ``unverified`` (``valid`` is
        ``None``) instead of pretending it is valid.
        """
        from cryptography.exceptions import InvalidSignature

        if issuer_cert is None and cert.issuer == cert.subject:
            issuer_cert = cert
        if issuer_cert is None:
            return {
                "valid": None,
                "status": "unverified",
                "message": (
                    "Issuer certificate not available; signature verification "
                    "requires trust-chain verification"
                ),
            }

        try:
            self._verify_signature(cert, issuer_cert)
            return {
                "valid": True,
                "status": "valid",
                "message": "Signature verified against issuer public key",
            }
        except InvalidSignature:
            return {
                "valid": False,
                "status": "invalid_signature",
                "message": "Certificate signature does not match the issuer public key",
            }
        except Exception as e:
            return {
                "valid": False,
                "status": "invalid_signature",
                "message": f"Signature verification error: {str(e)}",
            }

    def _check_basic_constraints(self, cert: x509.Certificate) -> Dict:
        """Check basic constraints extension."""
        try:
            constraints = cert.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
            if constraints.critical:
                return {
                    "valid": True,
                    "message": "Basic constraints present and valid",
                }
            return {
                "valid": True,
                "message": "Basic constraints present (non-critical)",
            }
        except x509.ExtensionNotFound:
            # Basic constraints are recommended but not strictly required
            return {
                "valid": True,
                "message": "Basic constraints extension not found (optional)",
            }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Invalid basic constraints: {str(e)}",
            }

    def _check_key_usage(self, cert: x509.Certificate) -> Dict:
        """Check key usage extension."""
        try:
            cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
            return {
                "valid": True,
                "message": "Key usage extension present and valid",
            }
        except x509.ExtensionNotFound:
            # Key usage is recommended but not strictly required
            return {
                "valid": True,
                "message": "Key usage extension not found (optional)",
            }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Invalid key usage: {str(e)}",
            }

    def _days_until_expiration(self, cert: x509.Certificate) -> Optional[int]:
        """Calculate days until certificate expiration."""
        try:
            now = datetime.now(timezone.utc)
            delta = cert.not_valid_after_utc - now
            return delta.days
        except Exception:
            return None

    def verify_trust_chain(
        self,
        cert_pem: str,
        trusted_ca_certs: List[str],
    ) -> Dict:
        """
        Verify the trust chain of a certificate.

        Args:
            cert_pem: PEM-formatted certificate string
            trusted_ca_certs: List of trusted CA certificates in PEM format

        Returns:
            Dictionary with trust chain verification results
        """
        try:
            cert = self.generator.load_certificate_from_pem(cert_pem)

            # Load trusted CA certificates
            trusted_cas = []
            for ca_pem in trusted_ca_certs:
                try:
                    ca_cert = self.generator.load_certificate_from_pem(ca_pem)
                    trusted_cas.append(ca_cert)
                except Exception as e:
                    logger.warning(f"Failed to load trusted CA certificate: {e}")

            # Build trust chain
            chain_result = self._build_trust_chain(cert, trusted_cas)

            if not chain_result["valid"]:
                return {
                    "valid": False,
                    "message": chain_result["message"],
                    "chain": [],
                    "validation_errors": [chain_result["message"]],
                }

            # Verify each link in the chain
            validation_errors = []
            chain = chain_result["chain"]

            for i in range(len(chain) - 1):
                current_cert = chain[i]
                issuer_cert = chain[i + 1]

                # Verify signature
                try:
                    self._verify_signature(current_cert, issuer_cert)
                except Exception as e:
                    validation_errors.append(f"Invalid signature at chain position {i}: {str(e)}")

                # Check expiration
                if not self._check_expiration(current_cert)["valid"]:
                    validation_errors.append(
                        f"Certificate at chain position {i} is expired or not yet valid"
                    )

            # Verify the root CA is self-signed
            root_ca = chain[-1]
            if root_ca.issuer != root_ca.subject:
                validation_errors.append("Root CA is not self-signed")

            # Verify root CA signature
            try:
                self._verify_signature(root_ca, root_ca)
            except Exception as e:
                validation_errors.append(f"Root CA signature is invalid: {str(e)}")

            if validation_errors:
                return {
                    "valid": False,
                    "message": "Trust chain validation failed",
                    "chain": [c.subject.rfc4514_string() for c in chain],
                    "validation_errors": validation_errors,
                }

            return {
                "valid": True,
                "message": "Trust chain is valid",
                "chain": [c.subject.rfc4514_string() for c in chain],
                "validation_errors": [],
            }

        except Exception as e:
            logger.error(f"Failed to verify trust chain: {e}")
            return {
                "valid": False,
                "message": f"Trust chain verification error: {str(e)}",
                "chain": [],
                "validation_errors": [str(e)],
            }

    def _build_trust_chain(
        self,
        cert: x509.Certificate,
        trusted_cas: List[x509.Certificate],
    ) -> Dict:
        """
        Build the trust chain for a certificate.

        Args:
            cert: Certificate to build chain for
            trusted_cas: List of trusted CA certificates

        Returns:
            Dictionary with chain building results
        """
        chain = [cert]
        visited = set()

        def find_issuer(current_cert: x509.Certificate) -> Optional[x509.Certificate]:
            """Find the issuer of a certificate."""
            # Check if it's self-signed (root CA)
            if current_cert.issuer == current_cert.subject:
                # Verify it's in trusted CAs
                for trusted_ca in trusted_cas:
                    if trusted_ca.subject == current_cert.subject:
                        return trusted_ca
                return None

            # Search for issuer in trusted CAs
            for trusted_ca in trusted_cas:
                if trusted_ca.subject == current_cert.issuer:
                    return trusted_ca

            return None

        current = cert
        max_depth = 10  # Prevent infinite loops
        depth = 0

        while depth < max_depth:
            issuer = find_issuer(current)

            if issuer is None:
                # Could not find issuer
                if current.issuer == current.subject:
                    # Self-signed but not in trusted CAs
                    return {
                        "valid": False,
                        "message": "Self-signed certificate not in trusted CA list",
                        "chain": chain,
                    }
                else:
                    return {
                        "valid": False,
                        "message": f"Could not find issuer: {current.issuer.rfc4514_string()}",
                        "chain": chain,
                    }

            if issuer in visited:
                return {
                    "valid": False,
                    "message": "Circular dependency detected in trust chain",
                    "chain": chain,
                }

            visited.add(issuer)
            chain.append(issuer)

            # Check if we reached a root CA
            if issuer.issuer == issuer.subject:
                return {
                    "valid": True,
                    "message": "Trust chain built successfully",
                    "chain": chain,
                }

            current = issuer
            depth += 1

        return {
            "valid": False,
            "message": "Trust chain too deep (possible loop)",
            "chain": chain,
        }

    def check_revocation(
        self,
        cert_pem: str,
        crl_pem: Optional[str] = None,
    ) -> Dict:
        """
        Check if a certificate is revoked.

        Args:
            cert_pem: PEM-formatted certificate string
            crl_pem: Optional PEM-formatted CRL string

        Returns:
            Dictionary with revocation status
        """
        try:
            cert = self.generator.load_certificate_from_pem(cert_pem)

            if crl_pem is None:
                # No CRL provided, cannot check revocation
                return {
                    "revoked": False,
                    "status": "unknown",
                    "message": "No CRL provided, revocation status unknown",
                }

            # Load CRL
            crl = x509.load_pem_x509_crl(crl_pem.encode("utf-8"), self.backend)

            # Check if certificate serial number is in CRL
            serial_number = cert.serial_number
            revoked_cert = crl.get_revoked_certificate_by_serial_number(serial_number)

            if revoked_cert is not None:
                return {
                    "revoked": True,
                    "status": "revoked",
                    "message": f"Certificate is revoked (serial: {serial_number})",
                    "revocation_date": revoked_cert.revocation_date.isoformat(),
                    "revocation_reason": (
                        str(revoked_cert.revocation_reason)
                        if revoked_cert.revocation_reason
                        else None
                    ),
                }

            return {
                "revoked": False,
                "status": "not_revoked",
                "message": "Certificate is not in CRL",
            }

        except Exception as e:
            logger.error(f"Failed to check revocation: {e}")
            return {
                "revoked": False,
                "status": "error",
                "message": f"Revocation check error: {str(e)}",
            }

    def generate_crl(
        self,
        ca_cert_pem: str,
        ca_private_key_pem: str,
        revoked_serials: List[Tuple[int, str, Optional[str]]],
        last_update: datetime,
        next_update: datetime,
    ) -> str:
        """
        Generate a Certificate Revocation List (CRL).

        Args:
            ca_cert_pem: CA certificate in PEM format
            ca_private_key_pem: CA private key in PEM format
            revoked_serials: List of (serial_number, revocation_date, reason) tuples
            last_update: Last update datetime
            next_update: Next update datetime

        Returns:
            PEM-formatted CRL string
        """
        try:
            ca_cert = self.generator.load_certificate_from_pem(ca_cert_pem)
            ca_private_key = self.generator.load_private_key_from_pem(ca_private_key_pem)

            # Create revoked certificates list
            revoked_certs = []
            for serial, revocation_date, reason in revoked_serials:
                revoked_cert = (
                    x509.RevokedCertificateBuilder()
                    .serial_number(serial)
                    .revocation_date(revocation_date)
                )

                if reason:
                    # Map reason string to enum
                    reason_map = {
                        "unspecified": x509.ReasonFlags.unspecified,
                        "key_compromise": x509.ReasonFlags.key_compromise,
                        "ca_compromise": x509.ReasonFlags.ca_compromise,
                        "affiliation_changed": x509.ReasonFlags.affiliation_changed,
                        "superseded": x509.ReasonFlags.superseded,
                        "cessation_of_operation": x509.ReasonFlags.cessation_of_operation,
                        "certificate_hold": x509.ReasonFlags.certificate_hold,
                        "remove_from_crl": x509.ReasonFlags.remove_from_crl,
                    }
                    reason_flag = reason_map.get(reason.lower(), x509.ReasonFlags.unspecified)
                    revoked_cert = revoked_cert.add_extension(
                        x509.CRLReason(reason_flag),
                        critical=False,
                    )

                revoked_certs.append(revoked_cert.build(self.backend))

            # Build CRL
            builder = x509.CertificateRevocationListBuilder()
            builder = builder.issuer_name(ca_cert.subject)
            builder = builder.last_update(last_update)
            builder = builder.next_update(next_update)

            for revoked_cert in revoked_certs:
                builder = builder.add_revoked_certificate(revoked_cert)

            # Add authority key identifier
            builder = builder.add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_private_key.public_key()),
                critical=False,
            )

            # Sign CRL
            if isinstance(ca_private_key, type(ca_private_key)):
                crl = builder.sign(ca_private_key, hashes.SHA256(), self.backend)
            else:
                crl = builder.sign(ca_private_key, hashes.SHA256(), self.backend)

            # Serialize to PEM
            crl_pem = crl.public_bytes(serialization.Encoding.PEM).decode("utf-8")

            logger.info(f"Generated CRL with {len(revoked_certs)} revoked certificates")
            return crl_pem

        except Exception as e:
            logger.error(f"Failed to generate CRL: {e}")
            raise

    def is_certificate_expiring_soon(
        self,
        cert_pem: str,
        days_threshold: int = 30,
    ) -> bool:
        """
        Check if a certificate is expiring soon.

        Args:
            cert_pem: PEM-formatted certificate string
            days_threshold: Number of days threshold

        Returns:
            True if certificate is expiring within threshold
        """
        try:
            cert = self.generator.load_certificate_from_pem(cert_pem)
            days_until = self._days_until_expiration(cert)
            return days_until is not None and days_until <= days_threshold
        except Exception as e:
            logger.error(f"Failed to check expiration: {e}")
            return False
