"""
Deployment Orchestrator - Handles deployment orchestration between environments
"""

import uuid
import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import queue

try:
    from .config_sync import SyncStrategy
except ImportError:
    from config_sync import SyncStrategy


class DeploymentStatus(Enum):
    """Deployment status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentType(Enum):
    """Deployment types"""
    FULL = "full"
    INCREMENTAL = "incremental"
    ROLLBACK = "rollback"


@dataclass
class DeploymentStep:
    """Single deployment step"""
    name: str
    description: str
    status: str = "pending"
    started_at: int = 0
    completed_at: int = 0
    error_message: str = ""


@dataclass
class Deployment:
    """Deployment record"""
    id: str
    source_env_id: str
    target_env_id: str
    deployment_type: str
    status: str
    progress: int = 0
    current_step: str = ""
    steps: List[DeploymentStep] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    parameters: Dict[str, str] = field(default_factory=dict)
    started_at: int = 0
    completed_at: int = 0
    rollback_id: str = ""


class DeploymentOrchestrator:
    """Orchestrates deployments between environments"""
    
    def __init__(self, environment_manager, config_sync):
        """
        Initialize the deployment orchestrator
        
        Args:
            environment_manager: EnvironmentManager instance
            config_sync: ConfigSync instance
        """
        self.environment_manager = environment_manager
        self.config_sync = config_sync
        self.deployments: Dict[str, Deployment] = {}
        self.lock = threading.RLock()
        self.deployment_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        
        # Start the deployment worker
        self._start_worker()
    
    def _start_worker(self):
        """Start the deployment worker thread"""
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._deployment_worker,
            daemon=True
        )
        self.worker_thread.start()
    
    def _deployment_worker(self):
        """Worker thread that processes deployments"""
        while self.running:
            try:
                deployment_id = self.deployment_queue.get(timeout=1)
                if deployment_id:
                    self._execute_deployment(deployment_id)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Deployment worker error: {e}")
    
    def deploy_to_environment(
        self,
        source_env_id: str,
        target_env_id: str,
        deployment_type: str = "full",
        parameters: Dict[str, str] = None
    ) -> Deployment:
        """
        Initiate a deployment to an environment
        
        Args:
            source_env_id: Source environment ID
            target_env_id: Target environment ID
            deployment_type: Type of deployment (full, incremental, rollback)
            parameters: Additional deployment parameters
            
        Returns:
            Deployment object
        """
        with self.lock:
            # Validate environments
            source_env = self.environment_manager.get_environment(source_env_id)
            target_env = self.environment_manager.get_environment(target_env_id)
            
            if not source_env:
                raise ValueError(f"Source environment {source_env_id} not found")
            
            if not target_env:
                raise ValueError(f"Target environment {target_env_id} not found")
            
            # Validate deployment type
            if deployment_type not in [e.value for e in DeploymentType]:
                raise ValueError(
                    f"Invalid deployment type: {deployment_type}. "
                    f"Must be one of {[e.value for e in DeploymentType]}"
                )
            
            # Validate deployment is allowed
            if not self._validate_deployment_allowed(source_env, target_env):
                raise ValueError(
                    f"Deployment not allowed from {source_env.type} to {target_env.type}"
                )
            
            # Create deployment record
            deployment = Deployment(
                id=str(uuid.uuid4()),
                source_env_id=source_env_id,
                target_env_id=target_env_id,
                deployment_type=deployment_type,
                status=DeploymentStatus.PENDING.value,
                progress=0,
                current_step="",
                parameters=parameters or {},
                started_at=int(time.time()),
                completed_at=0
            )
            
            # Create deployment steps based on type
            deployment.steps = self._create_deployment_steps(deployment_type)
            
            self.deployments[deployment.id] = deployment
            
            # Add to queue for processing
            self.deployment_queue.put(deployment.id)
            
            return deployment
    
    def _validate_deployment_allowed(self, source_env, target_env) -> bool:
        """
        Validate if deployment is allowed between environment types
        
        Args:
            source_env: Source environment
            target_env: Target environment
            
        Returns:
            True if deployment is allowed
        """
        # Define allowed deployment transitions
        allowed_transitions = {
            'dev': ['dev', 'staging'],
            'staging': ['staging', 'prod'],
            'prod': ['prod']  # Prod can only deploy to itself
        }
        
        allowed_targets = allowed_transitions.get(source_env.type, [])
        return target_env.type in allowed_targets
    
    def _create_deployment_steps(self, deployment_type: str) -> List[DeploymentStep]:
        """
        Create deployment steps based on deployment type
        
        Args:
            deployment_type: Type of deployment
            
        Returns:
            List of deployment steps
        """
        if deployment_type == DeploymentType.FULL.value:
            return [
                DeploymentStep(
                    name="validate_source",
                    description="Validate source environment"
                ),
                DeploymentStep(
                    name="validate_target",
                    description="Validate target environment"
                ),
                DeploymentStep(
                    name="backup_target",
                    description="Backup target environment configuration"
                ),
                DeploymentStep(
                    name="sync_config",
                    description="Synchronize configuration"
                ),
                DeploymentStep(
                    name="sync_variables",
                    description="Synchronize environment variables"
                ),
                DeploymentStep(
                    name="verify_deployment",
                    description="Verify deployment"
                ),
                DeploymentStep(
                    name="health_check",
                    description="Perform health check"
                )
            ]
        elif deployment_type == DeploymentType.INCREMENTAL.value:
            return [
                DeploymentStep(
                    name="validate_source",
                    description="Validate source environment"
                ),
                DeploymentStep(
                    name="validate_target",
                    description="Validate target environment"
                ),
                DeploymentStep(
                    name="sync_config",
                    description="Synchronize configuration changes"
                ),
                DeploymentStep(
                    name="verify_deployment",
                    description="Verify deployment"
                )
            ]
        elif deployment_type == DeploymentType.ROLLBACK.value:
            return [
                DeploymentStep(
                    name="validate_deployment",
                    description="Validate deployment to rollback"
                ),
                DeploymentStep(
                    name="restore_backup",
                    description="Restore from backup"
                ),
                DeploymentStep(
                    name="verify_rollback",
                    description="Verify rollback"
                ),
                DeploymentStep(
                    name="health_check",
                    description="Perform health check"
                )
            ]
        else:
            return []
    
    def _execute_deployment(self, deployment_id: str):
        """
        Execute a deployment
        
        Args:
            deployment_id: Deployment ID
        """
        with self.lock:
            deployment = self.deployments.get(deployment_id)
            if not deployment:
                return
            
            deployment.status = DeploymentStatus.IN_PROGRESS.value
            deployment.started_at = int(time.time())
        
        try:
            # Execute each step
            total_steps = len(deployment.steps)
            for i, step in enumerate(deployment.steps):
                with self.lock:
                    deployment.current_step = step.name
                    step.status = "in_progress"
                    step.started_at = int(time.time())
                
                # Execute the step
                success = self._execute_step(deployment, step)
                
                with self.lock:
                    if success:
                        step.status = "completed"
                        step.completed_at = int(time.time())
                        deployment.progress = int(((i + 1) / total_steps) * 100)
                        deployment.logs.append(f"Step '{step.name}' completed successfully")
                    else:
                        step.status = "failed"
                        step.completed_at = int(time.time())
                        deployment.status = DeploymentStatus.FAILED.value
                        deployment.logs.append(f"Step '{step.name}' failed: {step.error_message}")
                        deployment.completed_at = int(time.time())
                        return
            
            # All steps completed
            with self.lock:
                deployment.status = DeploymentStatus.COMPLETED.value
                deployment.completed_at = int(time.time())
                deployment.logs.append("Deployment completed successfully")
                
                # Update target environment status
                self.environment_manager.set_status(
                    deployment.target_env_id,
                    'active'
                )
                
        except Exception as e:
            with self.lock:
                deployment.status = DeploymentStatus.FAILED.value
                deployment.completed_at = int(time.time())
                deployment.logs.append(f"Deployment failed with error: {str(e)}")
    
    def _execute_step(self, deployment: Deployment, step: DeploymentStep) -> bool:
        """
        Execute a single deployment step
        
        Args:
            deployment: Deployment object
            step: Step to execute
            
        Returns:
            True if step succeeded
        """
        try:
            if step.name == "validate_source":
                return self._validate_source_environment(deployment)
            elif step.name == "validate_target":
                return self._validate_target_environment(deployment)
            elif step.name == "backup_target":
                return self._backup_target_environment(deployment)
            elif step.name == "sync_config":
                return self._sync_configuration(deployment)
            elif step.name == "sync_variables":
                return self._sync_variables(deployment)
            elif step.name == "verify_deployment":
                return self._verify_deployment(deployment)
            elif step.name == "health_check":
                return self._perform_health_check(deployment)
            elif step.name == "validate_deployment":
                return self._validate_deployment_for_rollback(deployment)
            elif step.name == "restore_backup":
                return self._restore_backup(deployment)
            elif step.name == "verify_rollback":
                return self._verify_rollback(deployment)
            else:
                step.error_message = f"Unknown step: {step.name}"
                return False
        except Exception as e:
            step.error_message = str(e)
            return False
    
    def _validate_source_environment(self, deployment: Deployment) -> bool:
        """Validate source environment"""
        source_env = self.environment_manager.get_environment(deployment.source_env_id)
        if not source_env:
            return False
        
        # Check if source is active
        if source_env.status != 'active':
            return False
        
        # Validate isolation
        if not self.environment_manager.validate_isolation(deployment.source_env_id):
            return False
        
        return True
    
    def _validate_target_environment(self, deployment: Deployment) -> bool:
        """Validate target environment"""
        target_env = self.environment_manager.get_environment(deployment.target_env_id)
        if not target_env:
            return False
        
        # Validate isolation
        if not self.environment_manager.validate_isolation(deployment.target_env_id):
            return False
        
        return True
    
    def _backup_target_environment(self, deployment: Deployment) -> bool:
        """Backup target environment configuration"""
        # In a real implementation, this would create a backup
        # For now, we'll store the config hash for potential rollback
        target_env = self.environment_manager.get_environment(deployment.target_env_id)
        if not target_env:
            return False
        
        deployment.parameters['backup_hash'] = self.environment_manager.get_environment_hash(
            deployment.target_env_id
        )
        
        return True
    
    def _sync_configuration(self, deployment: Deployment) -> bool:
        """Synchronize configuration"""
        result = self.config_sync.sync_config(
            deployment.source_env_id,
            deployment.target_env_id,
            strategy=SyncStrategy.MERGE
        )
        
        return result.success
    
    def _sync_variables(self, deployment: Deployment) -> bool:
        """Synchronize environment variables"""
        result = self.config_sync.sync_variables(
            deployment.source_env_id,
            deployment.target_env_id,
            include_secrets=False
        )
        
        return result.success
    
    def _verify_deployment(self, deployment: Deployment) -> bool:
        """Verify deployment by comparing configs"""
        comparison = self.config_sync.compare_configs(
            deployment.source_env_id,
            deployment.target_env_id
        )
        
        # For full deployment, we expect some differences (environment-specific)
        # For incremental, we expect minimal differences
        return comparison['success']
    
    def _perform_health_check(self, deployment: Deployment) -> bool:
        """Perform health check on target environment"""
        # In a real implementation, this would check actual health endpoints
        # For now, we'll simulate a health check
        target_env = self.environment_manager.get_environment(deployment.target_env_id)
        if not target_env:
            return False
        
        # Simulate health check
        return target_env.status == 'active'
    
    def _validate_deployment_for_rollback(self, deployment: Deployment) -> bool:
        """Validate deployment exists for rollback"""
        return deployment.source_env_id in self.deployments
    
    def _restore_backup(self, deployment: Deployment) -> bool:
        """Restore from backup"""
        # In a real implementation, this would restore from actual backup
        # For now, this is a placeholder
        return True
    
    def _verify_rollback(self, deployment: Deployment) -> bool:
        """Verify rollback"""
        return self._perform_health_check(deployment)
    
    def get_deployment_status(self, deployment_id: str) -> Optional[Deployment]:
        """
        Get deployment status
        
        Args:
            deployment_id: Deployment ID
            
        Returns:
            Deployment object or None if not found
        """
        with self.lock:
            return self.deployments.get(deployment_id)
    
    def list_deployments(
        self,
        source_env_id: str = None,
        target_env_id: str = None,
        status: str = None
    ) -> List[Deployment]:
        """
        List deployments with optional filters
        
        Args:
            source_env_id: Filter by source environment
            target_env_id: Filter by target environment
            status: Filter by status
            
        Returns:
            List of deployments
        """
        with self.lock:
            deployments = list(self.deployments.values())
            
            if source_env_id:
                deployments = [d for d in deployments if d.source_env_id == source_env_id]
            
            if target_env_id:
                deployments = [d for d in deployments if d.target_env_id == target_env_id]
            
            if status:
                deployments = [d for d in deployments if d.status == status]
            
            return deployments
    
    def rollback_deployment(
        self,
        deployment_id: str,
        reason: str = ""
    ) -> Optional[Deployment]:
        """
        Rollback a deployment
        
        Args:
            deployment_id: Deployment ID to rollback
            reason: Reason for rollback
            
        Returns:
            New rollback deployment or None if failed
        """
        with self.lock:
            original_deployment = self.deployments.get(deployment_id)
            if not original_deployment:
                return None
            
            if original_deployment.status != DeploymentStatus.COMPLETED.value:
                return None
        
        # Create a rollback deployment
        try:
            rollback_deployment = self.deploy_to_environment(
                source_env_id=original_deployment.target_env_id,
                target_env_id=original_deployment.source_env_id,
                deployment_type=DeploymentType.ROLLBACK.value,
                parameters={
                    'original_deployment_id': deployment_id,
                    'rollback_reason': reason
                }
            )
            
            # Update original deployment with rollback reference
            with self.lock:
                original_deployment.rollback_id = rollback_deployment.id
                original_deployment.status = DeploymentStatus.ROLLED_BACK.value
            
            return rollback_deployment
        except Exception as e:
            print(f"Rollback failed: {e}")
            return None
    
    def cancel_deployment(self, deployment_id: str) -> bool:
        """
        Cancel a pending or in-progress deployment
        
        Args:
            deployment_id: Deployment ID
            
        Returns:
            True if cancelled
        """
        with self.lock:
            deployment = self.deployments.get(deployment_id)
            if not deployment:
                return False
            
            if deployment.status in [DeploymentStatus.PENDING.value, DeploymentStatus.IN_PROGRESS.value]:
                deployment.status = "cancelled"
                deployment.completed_at = int(time.time())
                deployment.logs.append("Deployment cancelled")
                return True
            
            return False
    
    def stop(self):
        """Stop the deployment orchestrator"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
