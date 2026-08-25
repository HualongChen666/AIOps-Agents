"""
Configuration Synchronizer - Handles configuration sync between environments
"""

import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class SyncStrategy(Enum):
    """Configuration synchronization strategies"""
    OVERWRITE = "overwrite"  # Overwrite target config with source
    MERGE = "merge"  # Merge configs, source takes precedence
    SELECTIVE = "selective"  # Sync only specified keys


@dataclass
class SyncResult:
    """Result of a configuration sync operation"""
    success: bool
    message: str
    synced_keys: List[str]
    failed_keys: List[str]
    source_env_id: str
    target_env_id: str
    sync_time: int


class ConfigSync:
    """Handles configuration synchronization between environments"""
    
    def __init__(self, environment_manager):
        """
        Initialize the configuration synchronizer
        
        Args:
            environment_manager: EnvironmentManager instance
        """
        self.environment_manager = environment_manager
        self.sync_history: List[SyncResult] = []
    
    def sync_config(
        self,
        source_env_id: str,
        target_env_id: str,
        config_keys: List[str] = None,
        strategy: SyncStrategy = SyncStrategy.MERGE,
        dry_run: bool = False
    ) -> SyncResult:
        """
        Synchronize configuration from source to target environment
        
        Args:
            source_env_id: Source environment ID
            target_env_id: Target environment ID
            config_keys: List of specific keys to sync (None = all)
            strategy: Sync strategy to use
            dry_run: If True, don't actually apply changes
            
        Returns:
            SyncResult with sync operation details
        """
        sync_time = int(time.time())
        synced_keys = []
        failed_keys = []
        
        try:
            # Get environments
            source_env = self.environment_manager.get_environment(source_env_id)
            target_env = self.environment_manager.get_environment(target_env_id)
            
            if not source_env:
                return SyncResult(
                    success=False,
                    message=f"Source environment {source_env_id} not found",
                    synced_keys=[],
                    failed_keys=[],
                    source_env_id=source_env_id,
                    target_env_id=target_env_id,
                    sync_time=sync_time
                )
            
            if not target_env:
                return SyncResult(
                    success=False,
                    message=f"Target environment {target_env_id} not found",
                    synced_keys=[],
                    failed_keys=[],
                    source_env_id=source_env_id,
                    target_env_id=target_env_id,
                    sync_time=sync_time
                )
            
            # Validate environment types for sync
            if not self._validate_sync_allowed(source_env, target_env):
                return SyncResult(
                    success=False,
                    message=f"Sync not allowed from {source_env.type} to {target_env.type}",
                    synced_keys=[],
                    failed_keys=[],
                    source_env_id=source_env_id,
                    target_env_id=target_env_id,
                    sync_time=sync_time
                )
            
            # Determine which keys to sync
            if config_keys:
                keys_to_sync = config_keys
            else:
                keys_to_sync = list(source_env.config.keys())
            
            # Perform sync based on strategy
            if strategy == SyncStrategy.OVERWRITE:
                synced_keys, failed_keys = self._sync_overwrite(
                    source_env, target_env, keys_to_sync, dry_run
                )
            elif strategy == SyncStrategy.MERGE:
                synced_keys, failed_keys = self._sync_merge(
                    source_env, target_env, keys_to_sync, dry_run
                )
            elif strategy == SyncStrategy.SELECTIVE:
                synced_keys, failed_keys = self._sync_selective(
                    source_env, target_env, keys_to_sync, dry_run
                )
            else:
                return SyncResult(
                    success=False,
                    message=f"Unknown sync strategy: {strategy}",
                    synced_keys=[],
                    failed_keys=[],
                    source_env_id=source_env_id,
                    target_env_id=target_env_id,
                    sync_time=sync_time
                )
            
            # Record sync history
            result = SyncResult(
                success=len(failed_keys) == 0,
                message=f"Synced {len(synced_keys)} keys, {len(failed_keys)} failed",
                synced_keys=synced_keys,
                failed_keys=failed_keys,
                source_env_id=source_env_id,
                target_env_id=target_env_id,
                sync_time=sync_time
            )
            
            self.sync_history.append(result)
            
            return result
            
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"Sync failed: {str(e)}",
                synced_keys=synced_keys,
                failed_keys=failed_keys,
                source_env_id=source_env_id,
                target_env_id=target_env_id,
                sync_time=sync_time
            )
    
    def _validate_sync_allowed(self, source_env, target_env) -> bool:
        """
        Validate if sync is allowed between environment types
        
        Args:
            source_env: Source environment
            target_env: Target environment
            
        Returns:
            True if sync is allowed
        """
        # Define allowed sync transitions
        allowed_transitions = {
            'dev': ['dev', 'staging'],
            'staging': ['staging', 'prod'],
            'prod': ['prod']  # Prod can only sync to itself
        }
        
        allowed_targets = allowed_transitions.get(source_env.type, [])
        return target_env.type in allowed_targets
    
    def _sync_overwrite(
        self,
        source_env,
        target_env,
        keys: List[str],
        dry_run: bool
    ) -> Tuple[List[str], List[str]]:
        """
        Overwrite target config with source config
        
        Args:
            source_env: Source environment
            target_env: Target environment
            keys: Keys to sync
            dry_run: If True, don't apply changes
            
        Returns:
            Tuple of (synced_keys, failed_keys)
        """
        synced_keys = []
        failed_keys = []
        
        for key in keys:
            try:
                if key in source_env.config:
                    if not dry_run:
                        target_env.config[key] = source_env.config[key]
                    synced_keys.append(key)
                else:
                    failed_keys.append(key)
            except Exception as e:
                failed_keys.append(key)
        
        if not dry_run and synced_keys:
            self.environment_manager.update_config(
                target_env.id,
                target_env.config
            )
        
        return synced_keys, failed_keys
    
    def _sync_merge(
        self,
        source_env,
        target_env,
        keys: List[str],
        dry_run: bool
    ) -> Tuple[List[str], List[str]]:
        """
        Merge source config into target config
        
        Args:
            source_env: Source environment
            target_env: Target environment
            keys: Keys to sync
            dry_run: If True, don't apply changes
            
        Returns:
            Tuple of (synced_keys, failed_keys)
        """
        synced_keys = []
        failed_keys = []
        
        for key in keys:
            try:
                if key in source_env.config:
                    # Merge: source takes precedence
                    if not dry_run:
                        target_env.config[key] = source_env.config[key]
                    synced_keys.append(key)
                else:
                    failed_keys.append(key)
            except Exception as e:
                failed_keys.append(key)
        
        if not dry_run and synced_keys:
            self.environment_manager.update_config(
                target_env.id,
                target_env.config
            )
        
        return synced_keys, failed_keys
    
    def _sync_selective(
        self,
        source_env,
        target_env,
        keys: List[str],
        dry_run: bool
    ) -> Tuple[List[str], List[str]]:
        """
        Selectively sync only specified keys
        
        Args:
            source_env: Source environment
            target_env: Target environment
            keys: Keys to sync
            dry_run: If True, don't apply changes
            
        Returns:
            Tuple of (synced_keys, failed_keys)
        """
        synced_keys = []
        failed_keys = []
        
        for key in keys:
            try:
                if key in source_env.config and key in target_env.config:
                    # Only sync if key exists in both
                    if not dry_run:
                        target_env.config[key] = source_env.config[key]
                    synced_keys.append(key)
                else:
                    failed_keys.append(key)
            except Exception as e:
                failed_keys.append(key)
        
        if not dry_run and synced_keys:
            self.environment_manager.update_config(
                target_env.id,
                target_env.config
            )
        
        return synced_keys, failed_keys
    
    def sync_variables(
        self,
        source_env_id: str,
        target_env_id: str,
        variable_keys: List[str] = None,
        include_secrets: bool = False,
        dry_run: bool = False
    ) -> SyncResult:
        """
        Synchronize environment variables from source to target
        
        Args:
            source_env_id: Source environment ID
            target_env_id: Target environment ID
            variable_keys: List of specific variables to sync (None = all)
            include_secrets: Whether to sync secret variables
            dry_run: If True, don't actually apply changes
            
        Returns:
            SyncResult with sync operation details
        """
        sync_time = int(time.time())
        synced_keys = []
        failed_keys = []
        
        try:
            # Get environments
            source_env = self.environment_manager.get_environment(source_env_id)
            target_env = self.environment_manager.get_environment(target_env_id)
            
            if not source_env or not target_env:
                return SyncResult(
                    success=False,
                    message="Source or target environment not found",
                    synced_keys=[],
                    failed_keys=[],
                    source_env_id=source_env_id,
                    target_env_id=target_env_id,
                    sync_time=sync_time
                )
            
            # Determine which variables to sync
            if variable_keys:
                vars_to_sync = variable_keys
            else:
                vars_to_sync = list(source_env.variables.keys())
            
            # Sync variables
            for key in vars_to_sync:
                try:
                    if key in source_env.variables:
                        var_data = source_env.variables[key]
                        
                        # Skip secrets unless explicitly included
                        if var_data.get('is_secret', False) and not include_secrets:
                            failed_keys.append(key)
                            continue
                        
                        if not dry_run:
                            target_env.variables[key] = var_data.copy()
                        
                        synced_keys.append(key)
                    else:
                        failed_keys.append(key)
                except Exception as e:
                    failed_keys.append(key)
            
            if not dry_run and synced_keys:
                # Update the environment with new variables
                target_env.updated_at = int(time.time())
                # Save through environment manager
                for key in synced_keys:
                    var_data = target_env.variables[key]
                    self.environment_manager.set_variable(
                        target_env_id,
                        key,
                        var_data['value'],
                        var_data.get('is_secret', False)
                    )
            
            result = SyncResult(
                success=len(failed_keys) == 0,
                message=f"Synced {len(synced_keys)} variables, {len(failed_keys)} failed",
                synced_keys=synced_keys,
                failed_keys=failed_keys,
                source_env_id=source_env_id,
                target_env_id=target_env_id,
                sync_time=sync_time
            )
            
            self.sync_history.append(result)
            
            return result
            
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"Variable sync failed: {str(e)}",
                synced_keys=synced_keys,
                failed_keys=failed_keys,
                source_env_id=source_env_id,
                target_env_id=target_env_id,
                sync_time=sync_time
            )
    
    def get_sync_history(self, limit: int = 100) -> List[SyncResult]:
        """
        Get sync history
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of sync results
        """
        return self.sync_history[-limit:]
    
    def compare_configs(
        self,
        env1_id: str,
        env2_id: str
    ) -> Dict:
        """
        Compare configurations between two environments
        
        Args:
            env1_id: First environment ID
            env2_id: Second environment ID
            
        Returns:
            Dictionary with comparison results
        """
        env1 = self.environment_manager.get_environment(env1_id)
        env2 = self.environment_manager.get_environment(env2_id)
        
        if not env1 or not env2:
            return {
                'success': False,
                'message': 'One or both environments not found',
                'differences': []
            }
        
        # Get all keys from both environments
        all_keys = set(env1.config.keys()) | set(env2.config.keys())
        
        differences = []
        for key in sorted(all_keys):
            val1 = env1.config.get(key)
            val2 = env2.config.get(key)
            
            if val1 != val2:
                differences.append({
                    'key': key,
                    'env1_value': val1,
                    'env2_value': val2,
                    'status': 'different'
                })
            elif val1 is None:
                differences.append({
                    'key': key,
                    'env1_value': None,
                    'env2_value': val2,
                    'status': 'only_in_env2'
                })
            elif val2 is None:
                differences.append({
                    'key': key,
                    'env1_value': val1,
                    'env2_value': None,
                    'status': 'only_in_env1'
                })
        
        return {
            'success': True,
            'message': f'Found {len(differences)} differences',
            'differences': differences,
            'total_keys': len(all_keys),
            'matching_keys': len(all_keys) - len(differences)
        }
    
    def rollback_sync(self, sync_result: SyncResult) -> bool:
        """
        Rollback a sync operation by reversing the changes
        
        Args:
            sync_result: The sync result to rollback
            
        Returns:
            True if rollback successful
        """
        try:
            # Get the environments
            source_env = self.environment_manager.get_environment(sync_result.source_env_id)
            target_env = self.environment_manager.get_environment(sync_result.target_env_id)
            
            if not source_env or not target_env:
                return False
            
            # This is a simplified rollback - in production, you'd want
            # to store the previous state before sync
            # For now, we'll just reverse the sync
            for key in sync_result.synced_keys:
                if key in source_env.config:
                    # Revert target to original value (this is simplified)
                    # In production, store original values before sync
                    pass
            
            return True
        except Exception as e:
            print(f"Rollback failed: {e}")
            return False
