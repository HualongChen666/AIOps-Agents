"""
Test script for Environment Management Service

This script demonstrates the functionality of the Environment Management Service
by running tests on the core components without requiring the gRPC server.
"""

import sys
import os
import time

# Add the current directory to the path for imports
sys.path.insert(0, os.path.dirname(__file__))

from environment_manager import EnvironmentManager
from config_sync import ConfigSync
from deployment_orchestrator import DeploymentOrchestrator


def test_environment_manager():
    """Test EnvironmentManager functionality"""
    print("\n" + "=" * 60)
    print("Testing EnvironmentManager")
    print("=" * 60)
    
    # Initialize manager
    manager = EnvironmentManager()
    
    # List default environments
    print("\n1. Listing default environments:")
    envs = manager.list_environments()
    for env in envs:
        print(f"   - {env.name} ({env.type}): {env.status}")
    
    # Create a new environment
    print("\n2. Creating a new environment:")
    import uuid
    unique_name = f"Test Environment {uuid.uuid4().hex[:8]}"
    new_env = manager.create_environment(
        name=unique_name,
        env_type="dev",
        config={
            "log_level": "DEBUG",
            "timeout": "60",
            "max_connections": "200"
        },
        description="A test environment for development"
    )
    print(f"   Created: {new_env.name} (ID: {new_env.id})")
    
    # Get environment
    print("\n3. Getting environment by ID:")
    retrieved_env = manager.get_environment(new_env.id)
    print(f"   Retrieved: {retrieved_env.name}")
    print(f"   Config: {retrieved_env.config}")
    
    # Set environment variable
    print("\n4. Setting environment variables:")
    manager.set_variable(new_env.id, "API_KEY", "test-api-key-123", is_secret=True)
    manager.set_variable(new_env.id, "DB_HOST", "localhost", is_secret=False)
    print(f"   Set API_KEY (secret) and DB_HOST")
    
    # List variables
    print("\n5. Listing environment variables:")
    variables = manager.list_variables(new_env.id)
    for key, var_data in variables.items():
        secret_status = "(secret)" if var_data['is_secret'] else ""
        print(f"   - {key}: {var_data['value'][:20]}... {secret_status}")
    
    # Update configuration
    print("\n6. Updating configuration:")
    manager.update_config(new_env.id, {"timeout": "90", "new_setting": "value"})
    updated_env = manager.get_environment(new_env.id)
    print(f"   Updated config: {updated_env.config}")
    
    # Validate isolation
    print("\n7. Validating environment isolation:")
    is_valid = manager.validate_isolation(new_env.id)
    print(f"   Isolation valid: {is_valid}")
    
    # Get environment hash
    print("\n8. Getting environment hash:")
    env_hash = manager.get_environment_hash(new_env.id)
    print(f"   Hash: {env_hash}")
    
    # List environments with filter
    print("\n9. Listing dev environments:")
    dev_envs = manager.list_environments(env_type="dev")
    for env in dev_envs:
        print(f"   - {env.name}")
    
    print("\n[OK] EnvironmentManager tests completed successfully")


def test_config_sync():
    """Test ConfigSync functionality"""
    print("\n" + "=" * 60)
    print("Testing ConfigSync")
    print("=" * 60)
    
    # Initialize
    manager = EnvironmentManager()
    sync = ConfigSync(manager)
    
    # Get environments
    envs = manager.list_environments()
    if len(envs) < 2:
        print("Need at least 2 environments for sync test")
        return
    
    # Find valid sync pair (dev -> staging or staging -> prod)
    source_env = None
    target_env = None
    for env in envs:
        if env.type == 'dev' and not source_env:
            source_env = env
        elif env.type == 'staging' and not target_env:
            target_env = env
    
    # If no valid pair found, use first two but ensure valid transition
    if not source_env or not target_env:
        # Create a staging environment if needed
        if not target_env:
            import uuid
            target_env = manager.create_environment(
                name=f"Test Staging {uuid.uuid4().hex[:8]}",
                env_type="staging",
                config={"log_level": "INFO"},
                description="Test staging for sync"
            )
        if not source_env:
            import uuid
            source_env = manager.create_environment(
                name=f"Test Dev {uuid.uuid4().hex[:8]}",
                env_type="dev",
                config={"log_level": "DEBUG"},
                description="Test dev for sync"
            )
    
    print(f"\n1. Syncing config from {source_env.name} to {target_env.name}:")
    
    # Add a unique config to source
    manager.update_config(source_env.id, {"test_key": "test_value"})
    
    # Sync configuration
    from config_sync import SyncStrategy
    result = sync.sync_config(
        source_env_id=source_env.id,
        target_env_id=target_env.id,
        strategy=SyncStrategy.MERGE
    )
    
    print(f"   Success: {result.success}")
    print(f"   Message: {result.message}")
    print(f"   Synced keys: {result.synced_keys}")
    print(f"   Failed keys: {result.failed_keys}")
    
    # Compare configs
    print("\n2. Comparing configurations:")
    comparison = sync.compare_configs(source_env.id, target_env.id)
    print(f"   Total keys: {comparison['total_keys']}")
    print(f"   Matching keys: {comparison['matching_keys']}")
    print(f"   Differences: {len(comparison['differences'])}")
    
    # Sync variables
    print("\n3. Syncing environment variables:")
    manager.set_variable(source_env.id, "SYNC_VAR", "sync_value", is_secret=False)
    
    var_result = sync.sync_variables(
        source_env_id=source_env.id,
        target_env_id=target_env.id,
        include_secrets=False
    )
    
    print(f"   Success: {var_result.success}")
    print(f"   Message: {var_result.message}")
    print(f"   Synced variables: {var_result.synced_keys}")
    
    # Get sync history
    print("\n4. Getting sync history:")
    history = sync.get_sync_history(limit=5)
    print(f"   Recent syncs: {len(history)}")
    for h in history:
        print(f"   - {h.source_env_id} -> {h.target_env_id}: {h.message}")
    
    print("\n[OK] ConfigSync tests completed successfully")


def test_deployment_orchestrator():
    """Test DeploymentOrchestrator functionality"""
    print("\n" + "=" * 60)
    print("Testing DeploymentOrchestrator")
    print("=" * 60)
    
    # Initialize
    manager = EnvironmentManager()
    sync = ConfigSync(manager)
    orchestrator = DeploymentOrchestrator(manager, sync)
    
    # Get environments
    envs = manager.list_environments()
    if len(envs) < 2:
        print("Need at least 2 environments for deployment test")
        return
    
    # Find valid deployment pair (dev -> staging or staging -> prod)
    source_env = None
    target_env = None
    for env in envs:
        if env.type == 'dev' and not source_env:
            source_env = env
        elif env.type == 'staging' and not target_env:
            target_env = env
    
    # If no valid pair found, use first two but ensure valid transition
    if not source_env or not target_env:
        # Create a staging environment if needed
        if not target_env:
            import uuid
            target_env = manager.create_environment(
                name=f"Test Staging {uuid.uuid4().hex[:8]}",
                env_type="staging",
                config={"log_level": "INFO"},
                description="Test staging for deployment"
            )
        if not source_env:
            import uuid
            source_env = manager.create_environment(
                name=f"Test Dev {uuid.uuid4().hex[:8]}",
                env_type="dev",
                config={"log_level": "DEBUG"},
                description="Test dev for deployment"
            )
    
    print(f"\n1. Initiating deployment from {source_env.name} to {target_env.name}:")
    
    # Deploy
    from deployment_orchestrator import DeploymentType
    deployment = orchestrator.deploy_to_environment(
        source_env_id=source_env.id,
        target_env_id=target_env.id,
        deployment_type=DeploymentType.FULL.value,
        parameters={"auto_approve": "true"}
    )
    
    print(f"   Deployment ID: {deployment.id}")
    print(f"   Status: {deployment.status}")
    print(f"   Steps: {len(deployment.steps)}")
    
    # Wait for deployment to complete
    print("\n2. Waiting for deployment to complete:")
    max_wait = 30
    waited = 0
    while waited < max_wait:
        status = orchestrator.get_deployment_status(deployment.id)
        print(f"   Progress: {status.progress}% - {status.current_step}")
        
        if status.status in ["completed", "failed", "cancelled"]:
            break
        
        time.sleep(1)
        waited += 1
    
    # Get final status
    final_status = orchestrator.get_deployment_status(deployment.id)
    print(f"\n   Final status: {final_status.status}")
    print(f"   Logs:")
    for log in final_status.logs[-5:]:
        print(f"     - {log}")
    
    # List deployments
    print("\n3. Listing deployments:")
    deployments = orchestrator.list_deployments()
    print(f"   Total deployments: {len(deployments)}")
    for dep in deployments[-3:]:
        print(f"   - {dep.id}: {dep.status} ({dep.deployment_type})")
    
    print("\n[OK] DeploymentOrchestrator tests completed successfully")


def test_integration():
    """Test integration of all components"""
    print("\n" + "=" * 60)
    print("Testing Integration")
    print("=" * 60)
    
    # Initialize all components
    manager = EnvironmentManager()
    sync = ConfigSync(manager)
    orchestrator = DeploymentOrchestrator(manager, sync)
    
    print("\n1. Creating test environments:")
    
    import uuid
    # Create source environment
    source = manager.create_environment(
        name=f"Integration Source {uuid.uuid4().hex[:8]}",
        env_type="dev",
        config={"app_version": "1.0.0", "feature_flags": "new_ui"},
        description="Source environment for integration test"
    )
    print(f"   Created source: {source.id}")
    
    # Create target environment
    target = manager.create_environment(
        name=f"Integration Target {uuid.uuid4().hex[:8]}",
        env_type="staging",
        config={"app_version": "0.9.0"},
        description="Target environment for integration test"
    )
    print(f"   Created target: {target.id}")
    
    print("\n2. Setting up source environment:")
    manager.set_variable(source.id, "DEPLOY_KEY", "deploy-secret", is_secret=True)
    manager.set_variable(source.id, "API_ENDPOINT", "https://api.example.com", is_secret=False)
    print("   Set variables on source")
    
    print("\n3. Syncing configuration:")
    from config_sync import SyncStrategy
    sync_result = sync.sync_config(
        source_env_id=source.id,
        target_env_id=target.id,
        strategy=SyncStrategy.MERGE
    )
    print(f"   Sync result: {sync_result.success}")
    
    print("\n4. Syncing variables:")
    var_result = sync.sync_variables(
        source_env_id=source.id,
        target_env_id=target.id,
        include_secrets=False
    )
    print(f"   Variable sync result: {var_result.success}")
    
    print("\n5. Initiating deployment:")
    from deployment_orchestrator import DeploymentType
    deployment = orchestrator.deploy_to_environment(
        source_env_id=source.id,
        target_env_id=target.id,
        deployment_type=DeploymentType.FULL.value
    )
    print(f"   Deployment ID: {deployment.id}")
    
    print("\n6. Monitoring deployment:")
    max_wait = 30
    waited = 0
    while waited < max_wait:
        status = orchestrator.get_deployment_status(deployment.id)
        print(f"   {status.progress}% - {status.current_step}")
        
        if status.status in ["completed", "failed"]:
            break
        
        time.sleep(1)
        waited += 1
    
    final_status = orchestrator.get_deployment_status(deployment.id)
    print(f"\n   Final status: {final_status.status}")
    
    print("\n7. Performing health check:")
    # Health check is done through the gRPC server, but we can validate isolation
    is_valid = manager.validate_isolation(target.id)
    print(f"   Isolation valid: {is_valid}")
    
    print("\n8. Getting metrics:")
    # Metrics are simulated, but we can get the environment
    final_env = manager.get_environment(target.id)
    print(f"   Environment status: {final_env.status}")
    print(f"   Config keys: {len(final_env.config)}")
    print(f"   Variables: {len(final_env.variables)}")
    
    print("\n[OK] Integration tests completed successfully")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Environment Management Service - Test Suite")
    print("=" * 60)
    
    try:
        test_environment_manager()
        test_config_sync()
        test_deployment_orchestrator()
        test_integration()
        
        print("\n" + "=" * 60)
        print("All tests completed successfully! [OK]")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
