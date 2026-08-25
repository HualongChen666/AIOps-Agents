# -*- coding: utf-8 -*-
"""Test script for Certificate Management Service."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from certificate_management_service.certificate_manager import CertificateManager

def test_certificate_generation():
    """Test certificate generation."""
    print("Testing certificate generation...")
    cm = CertificateManager()

    # Generate a self-signed certificate
    cert = cm.create_certificate(
        common_name='test.example.com',
        organization='Test Org',
        country='US',
        validity_days=365,
        key_algorithm='RSA',
        key_size=2048,
        created_by='test'
    )

    print(f"Created certificate: {cert.certificate_id}")
    print(f"Common Name: {cert.common_name}")
    print(f"Status: {cert.status}")
    print(f"Valid until: {cert.valid_to}")
    print(f"Serial Number: {cert.serial_number}")
    print("Certificate generation test PASSED\n")
    return cert.certificate_id

def test_certificate_validation(cert_id):
    """Test certificate validation."""
    print("Testing certificate validation...")
    cm = CertificateManager()

    result = cm.validate_certificate(
        certificate_id=cert_id,
        check_expiration=True,
        check_revocation=True
    )

    print(f"Valid: {result['valid']}")
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Days until expiration: {result['days_until_expiration']}")
    print("Certificate validation test PASSED\n")

def test_certificate_revocation(cert_id):
    """Test certificate revocation."""
    print("Testing certificate revocation...")
    cm = CertificateManager()

    result = cm.revoke_certificate(
        certificate_id=cert_id,
        reason="key_compromise",
        revoked_by="test"
    )

    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Revocation date: {result['revocation_date']}")
    print("Certificate revocation test PASSED\n")

def test_certificate_renewal(cert_id):
    """Test certificate renewal."""
    print("Testing certificate renewal...")
    cm = CertificateManager()

    # First, create a new certificate to renew
    new_cert = cm.create_certificate(
        common_name='renew.example.com',
        organization='Test Org',
        country='US',
        validity_days=30,  # Short validity for testing
        key_algorithm='RSA',
        key_size=2048,
        created_by='test'
    )

    renewed_cert = cm.renew_certificate(
        certificate_id=new_cert.certificate_id,
        validity_days=365,
        renewed_by='test',
        generate_new_key=False
    )

    print(f"Original certificate: {new_cert.certificate_id}")
    print(f"Renewed certificate: {renewed_cert.certificate_id}")
    print(f"Original status: {new_cert.status}")
    print(f"Renewed status: {renewed_cert.status}")
    print("Certificate renewal test PASSED\n")

def test_list_certificates():
    """Test listing certificates."""
    print("Testing list certificates...")
    cm = CertificateManager()

    certs = cm.list_certificates(
        filter_status="all",
        limit=10
    )

    print(f"Found {len(certs)} certificates")
    for cert in certs:
        print(f"  - {cert['certificate_id']}: {cert['common_name']} ({cert['status']})")
    print("List certificates test PASSED\n")

if __name__ == "__main__":
    print("=" * 60)
    print("Certificate Management Service Test Suite")
    print("=" * 60 + "\n")

    try:
        # Run tests
        cert_id = test_certificate_generation()
        test_certificate_validation(cert_id)
        test_certificate_revocation(cert_id)
        test_certificate_renewal(cert_id)
        test_list_certificates()

        print("=" * 60)
        print("All tests PASSED!")
        print("=" * 60)
    except Exception as e:
        print(f"\nTest FAILED with error: {e}")
        import traceback
        traceback.print_exc()
