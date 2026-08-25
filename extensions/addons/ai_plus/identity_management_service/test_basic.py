# -*- coding: utf-8 -*-
"""Basic test to verify Identity Management Service can run."""

import asyncio
import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Add the service directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from group_manager import group_manager


async def test_group_manager():
    """Test basic group manager operations (doesn't require database)."""
    print("Testing Group Manager...")
    
    # Create a test group
    group = await group_manager.create_group(
        name="test_group",
        description="Test group for testing",
    )
    
    if group:
        print(f"[OK] Group created: {group['name']} (id={group['id']})")
    else:
        print("[FAIL] Failed to create group")
        return False
    
    # Get the group
    retrieved_group = await group_manager.get_group(group['id'])
    if retrieved_group:
        print(f"[OK] Group retrieved: {retrieved_group['name']}")
    else:
        print("[FAIL] Failed to retrieve group")
        return False
    
    # Update the group
    updated_group = await group_manager.update_group(
        group_id=group['id'],
        description="Updated description",
    )
    if updated_group:
        print(f"[OK] Group updated")
    else:
        print("[FAIL] Failed to update group")
        return False
    
    # List groups
    groups = await group_manager.list_groups()
    print(f"[OK] Groups listed: {len(groups)} groups")
    
    # Clean up
    deleted = await group_manager.delete_group(group['id'])
    if deleted:
        print(f"[OK] Group deleted")
    else:
        print("[FAIL] Failed to delete group")
        return False
    
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Identity Management Service - Basic Tests")
    print("=" * 60)
    
    results = []
    
    # Test group manager (doesn't require database)
    try:
        result = await test_group_manager()
        results.append(("Group Manager", result))
    except Exception as e:
        print(f"[FAIL] Group Manager test failed with error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Group Manager", False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    print("=" * 60)
    if all_passed:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
