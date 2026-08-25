# -*- coding: utf-8 -*-
"""Certificate Generator for Certificate Management Service."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import (
    dsa,
    ec,
    ed25519,
    rsa,
)
from cryptography.x509.oid import (
    NameOID,
    ExtensionOID,
)

try:
    from .config import Config
except ImportError:
    from config import Config

logger = logging.getLogger(Config.SERVICE_NAME)


class CertificateGenerator:
    """Generate X.509 certificates with real cryptographic operations."""

    def __init__(self):
        """Initialize the certificate generator."""
        self.backend = default_backend()

    def generate_key_pair(
        self,
        algorithm: str = "RSA",
        key_size: int = 2048,
    ) -> Tuple[object, object]:
        """
        Generate a public/private key pair.

        Args:
            algorithm: Key algorithm (RSA, ECDSA, Ed25519)
            key_size: Key size in bits

        Returns:
            Tuple of (private_key, public_key)

        Raises:
            ValueError: If algorithm or key size is invalid
        """
        try:
            if algorithm == "RSA":
                if key_size not in [2048, 4096, 8192]:
                    raise ValueError(f"Invalid RSA key size: {key_size}")
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=key_size,
                    backend=self.backend,
                )
                public_key = private_key.public_key()

            elif algorithm == "ECDSA":
                if key_size == 256:
                    curve = ec.SECP256R1()
                elif key_size == 384:
                    curve = ec.SECP384R1()
                elif key_size == 521:
                    curve = ec.SECP521R1()
                else:
                    raise ValueError(f"Invalid ECDSA key size: {key_size}")
                private_key = ec.generate_private_key(
                    curve=curve,
                    backend=self.backend,
                )
                public_key = private_key.public_key()

            elif algorithm == "Ed25519":
                private_key = ed25519.Ed25519PrivateKey.generate()
                public_key = private_key.public_key()

            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")

            logger.info(f"Generated {algorithm} key pair with size {key_size}")
            return private_key, public_key

        except Exception as e:
            logger.error(f"Failed to generate key pair: {e}")
            raise

    def serialize_private_key(
        self,
        private_key: object,
        password: Optional[bytes] = None,
    ) -> str:
        """
        Serialize private key to PEM format.

        Args:
            private_key: Private key object
            password: Optional password for encryption

        Returns:
            PEM-formatted private key string
        """
        encryption = (
            serialization.BestAvailableEncryption(password)
            if password
            else serialization.NoEncryption()
        )

        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption,
        )
        return pem.decode('utf-8')

    def serialize_public_key(self, public_key: object) -> str:
        """
        Serialize public key to PEM format.

        Args:
            public_key: Public key object

        Returns:
            PEM-formatted public key string
        """
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem.decode('utf-8')

    def create_certificate_builder(
        self,
        common_name: str,
        organization: str = "",
        organizational_unit: str = "",
        country: str = "",
        state: str = "",
        locality: str = "",
        email: str = "",
        san_dns: Optional[Dict[str, str]] = None,
        san_ip: Optional[List[str]] = None,
        san_email: Optional[List[str]] = None,
        extensions: Optional[Dict[str, str]] = None,
    ) -> x509.CertificateBuilder:
        """
        Create a certificate builder with subject information.

        Args:
            common_name: Common name (CN)
            organization: Organization (O)
            organizational_unit: Organizational Unit (OU)
            country: Country (C)
            state: State/Province (ST)
            locality: Locality (L)
            email: Email address
            san_dns: Subject Alternative Names - DNS
            san_ip: Subject Alternative Names - IP addresses
            san_email: Subject Alternative Names - Email
            extensions: Custom X.509 extensions

        Returns:
            CertificateBuilder object
        """
        # Build subject name
        name_attrs = []
        if common_name:
            name_attrs.append(x509.NameAttribute(NameOID.COMMON_NAME, common_name))
        if organization:
            name_attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization))
        if organizational_unit:
            name_attrs.append(x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, organizational_unit))
        if country:
            name_attrs.append(x509.NameAttribute(NameOID.COUNTRY_NAME, country))
        if state:
            name_attrs.append(x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state))
        if locality:
            name_attrs.append(x509.NameAttribute(NameOID.LOCALITY_NAME, locality))
        if email:
            name_attrs.append(x509.NameAttribute(NameOID.EMAIL_ADDRESS, email))

        subject = x509.Name(name_attrs)

        # Create builder
        builder = x509.CertificateBuilder()
        builder = builder.subject_name(subject)

        # Add Subject Alternative Names
        san_list = []
        if san_dns:
            for dns in san_dns.values():
                san_list.append(x509.DNSName(dns))
        if san_ip:
            for ip in san_ip:
                san_list.append(x509.IPAddress(ip))
        if san_email:
            for email_addr in san_email:
                san_list.append(x509.RFC822Name(email_addr))

        if san_list:
            builder = builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            )

        # Add custom extensions
        if extensions:
            for oid_value, value in extensions.items():
                try:
                    oid = x509.ObjectIdentifier(oid_value)
                    builder = builder.add_extension(
                        x509.UnrecognizedExtension(oid, value.encode()),
                        critical=False,
                    )
                except Exception as e:
                    logger.warning(f"Failed to add extension {oid_value}: {e}")

        return builder

    def generate_self_signed_certificate(
        self,
        common_name: str,
        private_key: object,
        public_key: object,
        organization: str = "",
        organizational_unit: str = "",
        country: str = "",
        state: str = "",
        locality: str = "",
        email: str = "",
        validity_days: int = 365,
        san_dns: Optional[Dict[str, str]] = None,
        san_ip: Optional[List[str]] = None,
        san_email: Optional[List[str]] = None,
        extensions: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, str]:
        """
        Generate a self-signed certificate.

        Args:
            common_name: Common name (CN)
            private_key: Private key for signing
            public_key: Public key for the certificate
            organization: Organization (O)
            organizational_unit: Organizational Unit (OU)
            country: Country (C)
            state: State/Province (ST)
            locality: Locality (L)
            email: Email address
            validity_days: Validity period in days
            san_dns: Subject Alternative Names - DNS
            san_ip: Subject Alternative Names - IP addresses
            san_email: Subject Alternative Names - Email
            extensions: Custom X.509 extensions

        Returns:
            Tuple of (certificate_pem, serial_number)
        """
        try:
            # Create builder
            builder = self.create_certificate_builder(
                common_name=common_name,
                organization=organization,
                organizational_unit=organizational_unit,
                country=country,
                state=state,
                locality=locality,
                email=email,
                san_dns=san_dns,
                san_ip=san_ip,
                san_email=san_email,
                extensions=extensions,
            )

            # Set issuer (self-signed)
            builder = builder.issuer_name(builder._subject_name)

            # Set validity period
            now = datetime.now(timezone.utc)
            builder = builder.not_valid_before(now)
            builder = builder.not_valid_after(now + timedelta(days=validity_days))

            # Set public key
            builder = builder.public_key(public_key)

            # Add basic constraints
            builder = builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )

            # Add key usage
            builder = builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )

            # Add extended key usage
            builder = builder.add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                ]),
                critical=False,
            )

            # Generate serial number
            serial_number = x509.random_serial_number()
            builder = builder.serial_number(serial_number)

            # Sign the certificate
            if isinstance(private_key, rsa.RSAPrivateKey):
                hash_algorithm = hashes.SHA256()
            elif isinstance(private_key, ec.EllipticCurvePrivateKey):
                hash_algorithm = hashes.SHA256()
            elif isinstance(private_key, ed25519.Ed25519PrivateKey):
                hash_algorithm = None  # Ed25519 uses its own signature
            else:
                hash_algorithm = hashes.SHA256()

            if hash_algorithm:
                certificate = builder.sign(private_key, hash_algorithm, self.backend)
            else:
                certificate = builder.sign(private_key, self.backend)

            # Serialize to PEM
            cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode('utf-8')

            logger.info(f"Generated self-signed certificate for {common_name}")
            return cert_pem, str(serial_number)

        except Exception as e:
            logger.error(f"Failed to generate self-signed certificate: {e}")
            raise

    def generate_ca_signed_certificate(
        self,
        common_name: str,
        private_key: object,
        public_key: object,
        ca_certificate: x509.Certificate,
        ca_private_key: object,
        organization: str = "",
        organizational_unit: str = "",
        country: str = "",
        state: str = "",
        locality: str = "",
        email: str = "",
        validity_days: int = 365,
        san_dns: Optional[Dict[str, str]] = None,
        san_ip: Optional[List[str]] = None,
        san_email: Optional[List[str]] = None,
        extensions: Optional[Dict[str, str]] = None,
        is_ca: bool = False,
        path_length: Optional[int] = None,
    ) -> Tuple[str, str]:
        """
        Generate a CA-signed certificate.

        Args:
            common_name: Common name (CN)
            private_key: Private key for the new certificate
            public_key: Public key for the new certificate
            ca_certificate: CA certificate object
            ca_private_key: CA private key for signing
            organization: Organization (O)
            organizational_unit: Organizational Unit (OU)
            country: Country (C)
            state: State/Province (ST)
            locality: Locality (L)
            email: Email address
            validity_days: Validity period in days
            san_dns: Subject Alternative Names - DNS
            san_ip: Subject Alternative Names - IP addresses
            san_email: Subject Alternative Names - Email
            extensions: Custom X.509 extensions
            is_ca: Whether this is a CA certificate
            path_length: Path length constraint for CA certificates

        Returns:
            Tuple of (certificate_pem, serial_number)
        """
        try:
            # Create builder
            builder = self.create_certificate_builder(
                common_name=common_name,
                organization=organization,
                organizational_unit=organizational_unit,
                country=country,
                state=state,
                locality=locality,
                email=email,
                san_dns=san_dns,
                san_ip=san_ip,
                san_email=san_email,
                extensions=extensions,
            )

            # Set issuer (CA)
            builder = builder.issuer_name(ca_certificate.subject)

            # Set validity period
            now = datetime.now(timezone.utc)
            builder = builder.not_valid_before(now)
            builder = builder.not_valid_after(now + timedelta(days=validity_days))

            # Set public key
            builder = builder.public_key(public_key)

            # Add basic constraints
            builder = builder.add_extension(
                x509.BasicConstraints(ca=is_ca, path_length=path_length),
                critical=True,
            )

            # Add key usage
            if is_ca:
                key_usage = x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                )
                extended_key_usage = x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CODE_SIGNING,
                ])
            else:
                key_usage = x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                )
                extended_key_usage = x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                ])

            builder = builder.add_extension(key_usage, critical=True)
            builder = builder.add_extension(extended_key_usage, critical=False)

            # Add Authority Key Identifier
            builder = builder.add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    ca_private_key.public_key()
                ),
                critical=False,
            )

            # Add Subject Key Identifier
            builder = builder.add_extension(
                x509.SubjectKeyIdentifier.from_public_key(public_key),
                critical=False,
            )

            # Generate serial number
            serial_number = x509.random_serial_number()
            builder = builder.serial_number(serial_number)

            # Sign the certificate with CA private key
            if isinstance(ca_private_key, rsa.RSAPrivateKey):
                hash_algorithm = hashes.SHA256()
            elif isinstance(ca_private_key, ec.EllipticCurvePrivateKey):
                hash_algorithm = hashes.SHA256()
            elif isinstance(ca_private_key, ed25519.Ed25519PrivateKey):
                hash_algorithm = None
            else:
                hash_algorithm = hashes.SHA256()

            if hash_algorithm:
                certificate = builder.sign(ca_private_key, hash_algorithm, self.backend)
            else:
                certificate = builder.sign(ca_private_key, self.backend)

            # Serialize to PEM
            cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode('utf-8')

            logger.info(f"Generated CA-signed certificate for {common_name}")
            return cert_pem, str(serial_number)

        except Exception as e:
            logger.error(f"Failed to generate CA-signed certificate: {e}")
            raise

    def generate_root_ca(
        self,
        common_name: str,
        private_key: object,
        public_key: object,
        organization: str = "",
        organizational_unit: str = "",
        country: str = "",
        state: str = "",
        locality: str = "",
        email: str = "",
        validity_days: int = 3650,
    ) -> Tuple[str, str]:
        """
        Generate a root CA certificate.

        Args:
            common_name: Common name (CN)
            private_key: Private key for the CA
            public_key: Public key for the CA
            organization: Organization (O)
            organizational_unit: Organizational Unit (OU)
            country: Country (C)
            state: State/Province (ST)
            locality: Locality (L)
            email: Email address
            validity_days: Validity period in days

        Returns:
            Tuple of (certificate_pem, serial_number)
        """
        try:
            # Create builder
            builder = self.create_certificate_builder(
                common_name=common_name,
                organization=organization,
                organizational_unit=organizational_unit,
                country=country,
                state=state,
                locality=locality,
                email=email,
            )

            # Set issuer (self-signed for root CA)
            builder = builder.issuer_name(builder._subject_name)

            # Set validity period
            now = datetime.now(timezone.utc)
            builder = builder.not_valid_before(now)
            builder = builder.not_valid_after(now + timedelta(days=validity_days))

            # Set public key
            builder = builder.public_key(public_key)

            # Add basic constraints for CA
            builder = builder.add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )

            # Add key usage for CA
            builder = builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )

            # Add extended key usage
            builder = builder.add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CODE_SIGNING,
                ]),
                critical=False,
            )

            # Add Subject Key Identifier
            builder = builder.add_extension(
                x509.SubjectKeyIdentifier.from_public_key(public_key),
                critical=False,
            )

            # Generate serial number
            serial_number = x509.random_serial_number()
            builder = builder.serial_number(serial_number)

            # Sign the certificate
            if isinstance(private_key, rsa.RSAPrivateKey):
                hash_algorithm = hashes.SHA256()
            elif isinstance(private_key, ec.EllipticCurvePrivateKey):
                hash_algorithm = hashes.SHA256()
            elif isinstance(private_key, ed25519.Ed25519PrivateKey):
                hash_algorithm = None
            else:
                hash_algorithm = hashes.SHA256()

            if hash_algorithm:
                certificate = builder.sign(private_key, hash_algorithm, self.backend)
            else:
                certificate = builder.sign(private_key, self.backend)

            # Serialize to PEM
            cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode('utf-8')

            logger.info(f"Generated root CA certificate for {common_name}")
            return cert_pem, str(serial_number)

        except Exception as e:
            logger.error(f"Failed to generate root CA certificate: {e}")
            raise

    def load_certificate_from_pem(self, cert_pem: str) -> x509.Certificate:
        """
        Load a certificate from PEM format.

        Args:
            cert_pem: PEM-formatted certificate string

        Returns:
            Certificate object
        """
        try:
            cert = x509.load_pem_x509_certificate(
                cert_pem.encode('utf-8'),
                self.backend,
            )
            return cert
        except Exception as e:
            logger.error(f"Failed to load certificate from PEM: {e}")
            raise

    def load_private_key_from_pem(
        self,
        key_pem: str,
        password: Optional[bytes] = None,
    ) -> object:
        """
        Load a private key from PEM format.

        Args:
            key_pem: PEM-formatted private key string
            password: Optional password for encrypted keys

        Returns:
            Private key object
        """
        try:
            private_key = serialization.load_pem_private_key(
                key_pem.encode('utf-8'),
                password=password,
                backend=self.backend,
            )
            return private_key
        except Exception as e:
            logger.error(f"Failed to load private key from PEM: {e}")
            raise

    def get_certificate_info(self, cert_pem: str) -> Dict:
        """
        Extract information from a certificate.

        Args:
            cert_pem: PEM-formatted certificate string

        Returns:
            Dictionary with certificate information
        """
        try:
            cert = self.load_certificate_from_pem(cert_pem)

            info = {
                "subject": {
                    "common_name": cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
                    if cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                    else "",
                    "organization": cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
                    if cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
                    else "",
                    "organizational_unit": cert.subject.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)[0].value
                    if cert.subject.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)
                    else "",
                    "country": cert.subject.get_attributes_for_oid(NameOID.COUNTRY_NAME)[0].value
                    if cert.subject.get_attributes_for_oid(NameOID.COUNTRY_NAME)
                    else "",
                    "state": cert.subject.get_attributes_for_oid(NameOID.STATE_OR_PROVINCE_NAME)[0].value
                    if cert.subject.get_attributes_for_oid(NameOID.STATE_OR_PROVINCE_NAME)
                    else "",
                    "locality": cert.subject.get_attributes_for_oid(NameOID.LOCALITY_NAME)[0].value
                    if cert.subject.get_attributes_for_oid(NameOID.LOCALITY_NAME)
                    else "",
                    "email": cert.subject.get_attributes_for_oid(NameOID.EMAIL_ADDRESS)[0].value
                    if cert.subject.get_attributes_for_oid(NameOID.EMAIL_ADDRESS)
                    else "",
                },
                "issuer": {
                    "common_name": cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
                    if cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
                    else "",
                },
                "serial_number": str(cert.serial_number),
                "not_valid_before": cert.not_valid_before_utc.isoformat(),
                "not_valid_after": cert.not_valid_after_utc.isoformat(),
                "signature_algorithm": cert.signature_algorithm_oid._name,
            }

            return info

        except Exception as e:
            logger.error(f"Failed to get certificate info: {e}")
            raise
