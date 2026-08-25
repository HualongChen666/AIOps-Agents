"""
gRPC Server for Environment Management Service
"""

import grpc
from concurrent import futures
import time
import threading
from typing import Optional
import logging

from . import (
    environment_management_pb2,
    environment_management_pb2_grpc
)
from ..environment_manager import EnvironmentManager
from ..config_sync import ConfigSync
from ..deployment_orchestrator import DeploymentOrchestrator


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnvironmentManagementServicer(environment_management_pb2_grpc.EnvironmentManagementServiceServicer):
    """gRPC service implementation for Environment Management"""
    
    def __init__(self):
        """Initialize the service with managers"""
        self.environment_manager = EnvironmentManager()
        self.config_sync = ConfigSync(self.environment_manager)
        self.deployment_orchestrator = DeploymentOrchestrator(
            self.environment_manager,
            self.config_sync
        )
        logger.info("Environment Management Service initialized")
    
    # Environment management methods
    
    def CreateEnvironment(self, request, context):
        """Create a new environment"""
        try:
            env = self.environment_manager.create_environment(
                name=request.name,
                env_type=request.type,
                config=dict(request.config),
                description=request.description
            )
            
            return environment_management_pb2.EnvironmentResponse(
                success=True,
                message="Environment created successfully",
                environment=self._environment_to_pb(env)
            )
        except Exception as e:
            logger.error(f"Error creating environment: {e}")
            return environment_management_pb2.EnvironmentResponse(
                success=False,
                message=str(e)
            )
    
    def GetEnvironment(self, request, context):
        """Get environment by ID"""
        try:
            env = self.environment_manager.get_environment(request.environment_id)
            
            if not env:
                return environment_management_pb2.EnvironmentResponse(
                    success=False,
                    message="Environment not found"
                )
            
            return environment_management_pb2.EnvironmentResponse(
                success=True,
                message="Environment retrieved successfully",
                environment=self._environment_to_pb(env)
            )
        except Exception as e:
            logger.error(f"Error getting environment: {e}")
            return environment_management_pb2.EnvironmentResponse(
                success=False,
                message=str(e)
            )
    
    def ListEnvironments(self, request, context):
        """List environments with optional filters"""
        try:
            env_type = request.type if request.type else None
            status = request.status if request.status else None
            
            environments = self.environment_manager.list_environments(
                env_type=env_type,
                status=status
            )
            
            return environment_management_pb2.ListEnvironmentsResponse(
                success=True,
                message="Environments retrieved successfully",
                environments=[self._environment_to_pb(env) for env in environments]
            )
        except Exception as e:
            logger.error(f"Error listing environments: {e}")
            return environment_management_pb2.ListEnvironmentsResponse(
                success=False,
                message=str(e)
            )
    
    def UpdateEnvironment(self, request, context):
        """Update environment configuration"""
        try:
            env = self.environment_manager.update_environment(
                environment_id=request.environment_id,
                config=dict(request.config) if request.config else None,
                description=request.description if request.description else None
            )
            
            return environment_management_pb2.EnvironmentResponse(
                success=True,
                message="Environment updated successfully",
                environment=self._environment_to_pb(env)
            )
        except Exception as e:
            logger.error(f"Error updating environment: {e}")
            return environment_management_pb2.EnvironmentResponse(
                success=False,
                message=str(e)
            )
    
    def DeleteEnvironment(self, request, context):
        """Delete an environment"""
        try:
            success = self.environment_manager.delete_environment(request.environment_id)
            
            if success:
                return environment_management_pb2.DeleteEnvironmentResponse(
                    success=True,
                    message="Environment deleted successfully"
                )
            else:
                return environment_management_pb2.DeleteEnvironmentResponse(
                    success=False,
                    message="Environment not found"
                )
        except Exception as e:
            logger.error(f"Error deleting environment: {e}")
            return environment_management_pb2.DeleteEnvironmentResponse(
                success=False,
                message=str(e)
            )
    
    # Configuration management methods
    
    def SyncConfig(self, request, context):
        """Synchronize configuration between environments"""
        try:
            config_keys = list(request.config_keys) if request.config_keys else None
            
            result = self.config_sync.sync_config(
                source_env_id=request.source_environment_id,
                target_env_id=request.target_environment_id,
                config_keys=config_keys
            )
            
            return environment_management_pb2.SyncConfigResponse(
                success=result.success,
                message=result.message,
                synced_keys=result.synced_keys,
                failed_keys=result.failed_keys
            )
        except Exception as e:
            logger.error(f"Error syncing config: {e}")
            return environment_management_pb2.SyncConfigResponse(
                success=False,
                message=str(e)
            )
    
    def GetConfig(self, request, context):
        """Get environment configuration"""
        try:
            config = self.environment_manager.get_config(request.environment_id)
            
            if config is None:
                return environment_management_pb2.ConfigResponse(
                    success=False,
                    message="Environment not found"
                )
            
            return environment_management_pb2.ConfigResponse(
                success=True,
                message="Configuration retrieved successfully",
                config=config
            )
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return environment_management_pb2.ConfigResponse(
                success=False,
                message=str(e)
            )
    
    def UpdateConfig(self, request, context):
        """Update environment configuration"""
        try:
            env = self.environment_manager.update_config(
                environment_id=request.environment_id,
                config=dict(request.config)
            )
            
            return environment_management_pb2.ConfigResponse(
                success=True,
                message="Configuration updated successfully",
                config=env.config
            )
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return environment_management_pb2.ConfigResponse(
                success=False,
                message=str(e)
            )
    
    # Deployment orchestration methods
    
    def DeployToEnvironment(self, request, context):
        """Deploy to an environment"""
        try:
            deployment = self.deployment_orchestrator.deploy_to_environment(
                source_env_id=request.source_environment_id,
                target_env_id=request.target_environment_id,
                deployment_type=request.deployment_type,
                parameters=dict(request.parameters)
            )
            
            return environment_management_pb2.DeployResponse(
                success=True,
                message="Deployment initiated successfully",
                deployment_id=deployment.id
            )
        except Exception as e:
            logger.error(f"Error deploying: {e}")
            return environment_management_pb2.DeployResponse(
                success=False,
                message=str(e)
            )
    
    def GetDeploymentStatus(self, request, context):
        """Get deployment status"""
        try:
            deployment = self.deployment_orchestrator.get_deployment_status(
                request.deployment_id
            )
            
            if not deployment:
                return environment_management_pb2.DeploymentStatusResponse(
                    success=False,
                    message="Deployment not found"
                )
            
            return environment_management_pb2.DeploymentStatusResponse(
                success=True,
                message="Deployment status retrieved successfully",
                status=self._deployment_status_to_pb(deployment)
            )
        except Exception as e:
            logger.error(f"Error getting deployment status: {e}")
            return environment_management_pb2.DeploymentStatusResponse(
                success=False,
                message=str(e)
            )
    
    def RollbackDeployment(self, request, context):
        """Rollback a deployment"""
        try:
            rollback = self.deployment_orchestrator.rollback_deployment(
                deployment_id=request.deployment_id,
                reason=request.reason
            )
            
            if not rollback:
                return environment_management_pb2.RollbackResponse(
                    success=False,
                    message="Rollback failed"
                )
            
            return environment_management_pb2.RollbackResponse(
                success=True,
                message="Rollback initiated successfully",
                rollback_id=rollback.id
            )
        except Exception as e:
            logger.error(f"Error rolling back deployment: {e}")
            return environment_management_pb2.RollbackResponse(
                success=False,
                message=str(e)
            )
    
    # Environment variable management methods
    
    def SetEnvironmentVariable(self, request, context):
        """Set an environment variable"""
        try:
            env = self.environment_manager.set_variable(
                environment_id=request.environment_id,
                key=request.key,
                value=request.value,
                is_secret=request.is_secret
            )
            
            var_data = env.variables.get(request.key, {})
            
            return environment_management_pb2.VariableResponse(
                success=True,
                message="Variable set successfully",
                variable=environment_management_pb2.EnvironmentVariable(
                    key=request.key,
                    value=var_data.get('value', ''),
                    is_secret=var_data.get('is_secret', False),
                    updated_at=var_data.get('updated_at', 0)
                )
            )
        except Exception as e:
            logger.error(f"Error setting variable: {e}")
            return environment_management_pb2.VariableResponse(
                success=False,
                message=str(e)
            )
    
    def GetEnvironmentVariable(self, request, context):
        """Get an environment variable"""
        try:
            var_data = self.environment_manager.get_variable(
                environment_id=request.environment_id,
                key=request.key
            )
            
            if not var_data:
                return environment_management_pb2.VariableResponse(
                    success=False,
                    message="Variable not found"
                )
            
            return environment_management_pb2.VariableResponse(
                success=True,
                message="Variable retrieved successfully",
                variable=environment_management_pb2.EnvironmentVariable(
                    key=request.key,
                    value=var_data.get('value', ''),
                    is_secret=var_data.get('is_secret', False),
                    updated_at=var_data.get('updated_at', 0)
                )
            )
        except Exception as e:
            logger.error(f"Error getting variable: {e}")
            return environment_management_pb2.VariableResponse(
                success=False,
                message=str(e)
            )
    
    def ListEnvironmentVariables(self, request, context):
        """List all environment variables"""
        try:
            variables = self.environment_manager.list_variables(request.environment_id)
            
            pb_variables = []
            for key, var_data in variables.items():
                pb_variables.append(
                    environment_management_pb2.EnvironmentVariable(
                        key=key,
                        value=var_data.get('value', ''),
                        is_secret=var_data.get('is_secret', False),
                        updated_at=var_data.get('updated_at', 0)
                    )
                )
            
            return environment_management_pb2.ListVariablesResponse(
                success=True,
                message="Variables retrieved successfully",
                variables=pb_variables
            )
        except Exception as e:
            logger.error(f"Error listing variables: {e}")
            return environment_management_pb2.ListVariablesResponse(
                success=False,
                message=str(e)
            )
    
    def DeleteEnvironmentVariable(self, request, context):
        """Delete an environment variable"""
        try:
            env = self.environment_manager.delete_variable(
                environment_id=request.environment_id,
                key=request.key
            )
            
            return environment_management_pb2.DeleteVariableResponse(
                success=True,
                message="Variable deleted successfully"
            )
        except Exception as e:
            logger.error(f"Error deleting variable: {e}")
            return environment_management_pb2.DeleteVariableResponse(
                success=False,
                message=str(e)
            )
    
    # Health check methods
    
    def HealthCheck(self, request, context):
        """Perform health check on environment"""
        try:
            env = self.environment_manager.get_environment(request.environment_id)
            
            if not env:
                return environment_management_pb2.HealthCheckResponse(
                    success=False,
                    message="Environment not found",
                    is_healthy=False
                )
            
            # Perform health checks
            checks = []
            
            # Check 1: Environment status
            status_check = environment_management_pb2.HealthCheckResult(
                check_name="status",
                passed=env.status == 'active',
                message=f"Environment status is {env.status}",
                response_time_ms=10
            )
            checks.append(status_check)
            
            # Check 2: Isolation validation
            isolation_check = environment_management_pb2.HealthCheckResult(
                check_name="isolation",
                passed=self.environment_manager.validate_isolation(request.environment_id),
                message="Environment isolation validated",
                response_time_ms=15
            )
            checks.append(isolation_check)
            
            # Check 3: Configuration integrity
            config_check = environment_management_pb2.HealthCheckResult(
                check_name="configuration",
                passed=len(env.config) > 0,
                message=f"Configuration has {len(env.config)} keys",
                response_time_ms=5
            )
            checks.append(config_check)
            
            # Overall health
            is_healthy = all(check.passed for check in checks)
            
            return environment_management_pb2.HealthCheckResponse(
                success=True,
                message="Health check completed",
                is_healthy=is_healthy,
                checks=checks
            )
        except Exception as e:
            logger.error(f"Error performing health check: {e}")
            return environment_management_pb2.HealthCheckResponse(
                success=False,
                message=str(e),
                is_healthy=False
            )
    
    def GetEnvironmentMetrics(self, request, context):
        """Get environment metrics"""
        try:
            env = self.environment_manager.get_environment(request.environment_id)
            
            if not env:
                return environment_management_pb2.MetricsResponse(
                    success=False,
                    message="Environment not found"
                )
            
            # In a real implementation, these would be actual metrics
            # For now, we'll simulate metrics based on environment type
            base_metrics = {
                'dev': {'cpu': 30, 'memory': 40, 'connections': 50},
                'staging': {'cpu': 45, 'memory': 55, 'connections': 200},
                'prod': {'cpu': 60, 'memory': 70, 'connections': 500}
            }
            
            metrics = base_metrics.get(env.type, base_metrics['dev'])
            
            uptime = int(time.time()) - env.created_at
            
            return environment_management_pb2.MetricsResponse(
                success=True,
                message="Metrics retrieved successfully",
                metrics=environment_management_pb2.EnvironmentMetrics(
                    environment_id=request.environment_id,
                    cpu_usage_percent=metrics['cpu'],
                    memory_usage_percent=metrics['memory'],
                    active_connections=metrics['connections'],
                    request_count=1000 + uptime * 10,
                    error_rate=0.01 if env.type == 'prod' else 0.05,
                    uptime_seconds=uptime
                )
            )
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return environment_management_pb2.MetricsResponse(
                success=False,
                message=str(e)
            )
    
    # Helper methods
    
    def _environment_to_pb(self, env) -> environment_management_pb2.Environment:
        """Convert Environment to protobuf"""
        return environment_management_pb2.Environment(
            id=env.id,
            name=env.name,
            type=env.type,
            config=env.config,
            description=env.description,
            status=env.status,
            created_at=env.created_at,
            updated_at=env.updated_at
        )
    
    def _deployment_status_to_pb(self, deployment) -> environment_management_pb2.DeploymentStatus:
        """Convert Deployment to protobuf"""
        return environment_management_pb2.DeploymentStatus(
            deployment_id=deployment.id,
            status=deployment.status,
            progress=deployment.progress,
            current_step=deployment.current_step,
            logs=deployment.logs,
            started_at=deployment.started_at,
            completed_at=deployment.completed_at
        )


def serve(host: str = '[::]', port: int = 50052, max_workers: int = 10):
    """
    Start the gRPC server
    
    Args:
        host: Host to bind to
        port: Port to bind to
        max_workers: Maximum number of worker threads
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    
    environment_management_pb2_grpc.add_EnvironmentManagementServiceServicer_to_server(
        EnvironmentManagementServicer(),
        server
    )
    
    server_address = f"{host}:{port}"
    server.add_insecure_port(server_address)
    
    logger.info(f"Starting Environment Management Service on {server_address}")
    server.start()
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.stop(0)


if __name__ == '__main__':
    serve()
