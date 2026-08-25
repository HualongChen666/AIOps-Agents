# -*- coding: utf-8 -*-
"""Test script for Secret Management Service."""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directories to path for proper package imports
service_dir = Path(__file__).parent
ai_plus_dir = service_dir.parent
addons_dir = ai_plus_dir.parent
extensions_dir = addons_dir.parent
project_root = extensions_dir.parent

sys.path.insert(0, str(project_root))

# Import as package
from extensions.addons.ai_plus.secret_management_service import config
from extensions.addons.ai_plus.secret_management_service import encryption_service
from extensions.addons.ai_plus.secret_management_service import access_control
from extensions.addons.ai_plus.secret_management_service import audit_log
from extensions.addons.ai_plus.secret_management_service import secret_manager


async def test_secret_manager():
    """Test the secret manager functionality."""
    print("Testing Secret Management Service...")
    print("=" * 60)

    # Initialize components
    print("\n1. Initializing components...")
    enc_service = encryption_service.EncryptionService()
    acc_control = access_control.AccessControl()
    audit = audit_log.AuditLog()
    secret_mgr = secret_manager.SecretManager(
        encryption_service=enc_service,
        access_control=acc_control,
    )
    print("[OK] Components initialized")

    # Test creating a secret
    print("\n2. Creating a secret...")
    secret = secret_mgr.create_secret(
        name="test_database_password",
        value="my_secure_password_123",
        description="Test database password",
        created_by="admin",
        tags={"environment": "test", "service": "database"},
        principal="admin",
    )
    print(f"[OK] Secret created: {secret.metadata.name} (ID: {secret.metadata.secret_id})")
    print(f"  Version: {secret.metadata.current_version}")
    print(f"  Status: {secret.metadata.status}")

    # Test getting secret metadata
    print("\n3. Getting secret metadata...")
    secret_data = secret_mgr.get_secret(
        secret_id=secret.metadata.secret_id,
        include_value=False,
        principal="admin",
    )
    print(f"[OK] Secret retrieved: {secret_data['metadata']['name']}")
    print(f"  Created at: {secret_data['metadata']['created_at']}")

    # Test getting secret with value
    print("\n4. Getting secret with decrypted value...")
    secret_with_value = secret_mgr.get_secret(
        secret_id=secret.metadata.secret_id,
        include_value=True,
        principal="admin",
    )
    print(f"[OK] Secret value: {secret_with_value['value']}")

    # Test updating secret
    print("\n5. Updating secret...")
    updated = secret_mgr.update_secret(
        secret_id=secret.metadata.secret_id,
        value="new_secure_password_456",
        description="Updated test database password",
        updated_by="admin",
        principal="admin",
    )
    print(f"[OK] Secret updated: Version {updated.metadata.current_version}")

    # Test listing secrets
    print("\n6. Listing secrets...")
    secrets = secret_mgr.list_secrets(filter_status="active", principal="admin")
    print(f"[OK] Found {len(secrets)} secret(s)")
    for s in secrets:
        print(f"  - {s['name']} (Status: {s['status']})")

    # Test secret versions
    print("\n7. Getting secret versions...")
    versions = secret_mgr.get_secret_versions(
        secret_id=secret.metadata.secret_id,
        principal="admin",
    )
    print(f"[OK] Found {len(versions)} version(s)")
    for v in versions:
        print(f"  - Version {v['version']} (Created: {v['created_at']})")

    # Test rotating secret
    print("\n8. Rotating secret...")
    rotated = secret_mgr.rotate_secret(
        secret_id=secret.metadata.secret_id,
        new_value="rotated_password_789",
        rotated_by="admin",
        principal="admin",
    )
    print(f"[OK] Secret rotated: Version {rotated.metadata.current_version}")

    # Test access control
    print("\n9. Testing access control...")
    acc_control.grant_access(
        secret_id=secret.metadata.secret_id,
        principal="test_user",
        principal_type="user",
        permissions=["read"],
        granted_by="admin",
    )
    print("[OK] Granted read access to test_user")

    permissions = acc_control.get_permissions(secret.metadata.secret_id)
    print(f"[OK] Current permissions: {len(permissions)} principal(s) with access")

    # Test audit log
    print("\n10. Testing audit log...")
    audit_entries = audit.get_by_secret(secret.metadata.secret_id, limit=5)
    print(f"[OK] Found {len(audit_entries)} audit log entries")
    for entry in audit_entries[:3]:
        print(f"  - {entry['action']} by {entry['principal']} at {entry['timestamp']}")

    # Test reverting version
    print("\n11. Reverting to previous version...")
    reverted = secret_mgr.revert_secret_version(
        secret_id=secret.metadata.secret_id,
        target_version=2,
        reverted_by="admin",
        principal="admin",
    )
    print(f"[OK] Reverted to version {reverted.metadata.current_version}")

    # Test deletion
    print("\n12. Deleting secret (soft delete)...")
    deleted = secret_mgr.delete_secret(
        secret_id=secret.metadata.secret_id,
        permanent=False,
        principal="admin",
    )
    print(f"[OK] Secret soft deleted: {deleted}")

    # Verify deletion
    print("\n13. Verifying deletion...")
    secrets_after = secret_mgr.list_secrets(filter_status="active", principal="admin")
    print(f"[OK] Active secrets after deletion: {len(secrets_after)}")

    # Test statistics
    print("\n14. Getting audit log statistics...")
    stats = audit.get_statistics()
    print(f"[OK] Total audit entries: {stats['total_entries']}")
    print(f"  By action: {stats['by_action']}")
    print(f"  By result: {stats['by_result']}")

    print("\n" + "=" * 60)
    print("[OK] All tests passed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_secret_manager())
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
