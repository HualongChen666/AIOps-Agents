"""
gRPC Client for Environment Management Service
"""

import grpc
from typing import Dict, List, Optional

from . import (
    environment_management_pb2,
    environment_management_pb2_grpc
)


class EnvironmentManagementClient:
    """Client for Environment Management Service"""
    
    def __init__(self, host: str = 'localhost', port: int = 50052):
        """
        Initialize the client
        
        Args:
            host: Server host
            port: Server port
        """
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = environment_management_pb2_grpc.EnvironmentManagementServiceStub(
            self.channel
        )
    
    def close(self):
        """Close the client connection"""
        self.channel.close()
    
    # Environment management methods
    
    def create_environment(
        self,
        name: str,
        env_type: str,
        config: Dict[str, str],
        description: str = ""
    ) -> Dict:
        """
        Create a new environment
        
        Args:
            name: Environment name
            env_type: Environment type (dev, staging, prod)
            config: Configuration dictionary
            description: Environment description
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.CreateEnvironmentRequest(
            name=name,
            type=env_type,
            config=config,
            description=description
        )
        
        response = self.stub.CreateEnvironment(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'environment': {
                'id': response.environment.id,
                'name': response.environment.name,
                'type': response.environment.type,
                'config': dict(response.environment.config),
                'description': response.environment.description,
                'status': response.environment.status,
                'created_at': response.environment.created_at,
                'updated_at': response.environment.updated_at
            } if response.HasField('environment') else None
        }
    
    def get_environment(self, environment_id: str) -> Dict:
        """
        Get environment by ID
        
        Args:
            environment_id: Environment ID
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.GetEnvironmentRequest(
            environment_id=environment_id
        )
        
        response = self.stub.GetEnvironment(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'environment': {
                'id': response.environment.id,
                'name': response.environment.name,
                'type': response.environment.type,
                'config': dict(response.environment.config),
                'description': response.environment.description,
                'status': response.environment.status,
                'created_at': response.environment.created_at,
                'updated_at': response.environment.updated_at
            } if response.HasField('environment') else None
        }
    
    def list_environments(
        self,
        env_type: str = None,
        status: str = None
    ) -> Dict:
        """
        List environments with optional filters
        
        Args:
            env_type: Filter by environment type
            status: Filter by status
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.ListEnvironmentsRequest(
            type=env_type or "",
            status=status or ""
        )
        
        response = self.stub.ListEnvironments(request)
        
        environments = []
        for env in response.environments:
            environments.append({
                'id': env.id,
                'name': env.name,
                'type': env.type,
                'config': dict(env.config),
                'description': env.description,
                'status': env.status,
                'created_at': env.created_at,
                'updated_at': env.updated_at
            })
        
        return {
            'success': response.success,
            'message': response.message,
            'environments': environments
        }
    
    def update_environment(
        self,
        environment_id: str,
        config: Dict[str, str] = None,
        description: str = None
    ) -> Dict:
        """
        Update environment configuration
        
        Args:
            environment_id: Environment ID
            config: New configuration (partial update)
            description: New description
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.UpdateEnvironmentRequest(
            environment_id=environment_id,
            config=config or {},
            description=description or ""
        )
        
        response = self.stub.UpdateEnvironment(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'environment': {
                'id': response.environment.id,
                'name': response.environment.name,
                'type': response.environment.type,
                'config': dict(response.environment.config),
                'description': response.environment.description,
                'status': response.environment.status,
                'created_at': response.environment.created_at,
                'updated_at': response.environment.updated_at
            } if response.HasField('environment') else None
        }
    
    def delete_environment(self, environment_id: str) -> Dict:
        """
        Delete an environment
        
        Args:
            environment_id: Environment ID
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.DeleteEnvironmentRequest(
            environment_id=environment_id
        )
        
        response = self.stub.DeleteEnvironment(request)
        
        return {
            'success': response.success,
            'message': response.message
        }
    
    # Configuration management methods
    
    def sync_config(
        self,
        source_environment_id: str,
        target_environment_id: str,
        config_keys: List[str] = None
    ) -> Dict:
        """
        Synchronize configuration between environments
        
        Args:
            source_environment_id: Source environment ID
            target_environment_id: Target environment ID
            config_keys: List of specific keys to sync (None = all)
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.SyncConfigRequest(
            source_environment_id=source_environment_id,
            target_environment_id=target_environment_id,
            config_keys=config_keys or []
        )
        
        response = self.stub.SyncConfig(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'synced_keys': list(response.synced_keys),
            'failed_keys': list(response.failed_keys)
        }
    
    def get_config(self, environment_id: str) -> Dict:
        """
        Get environment configuration
        
        Args:
            environment_id: Environment ID
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.GetConfigRequest(
            environment_id=environment_id
        )
        
        response = self.stub.GetConfig(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'config': dict(response.config)
        }
    
    def update_config(
        self,
        environment_id: str,
        config: Dict[str, str]
    ) -> Dict:
        """
        Update environment configuration
        
        Args:
            environment_id: Environment ID
            config: New configuration (partial update)
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.UpdateConfigRequest(
            environment_id=environment_id,
            config=config
        )
        
        response = self.stub.UpdateConfig(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'config': dict(response.config)
        }
    
    # Deployment orchestration methods
    
    def deploy_to_environment(
        self,
        source_environment_id: str,
        target_environment_id: str,
        deployment_type: str = "full",
        parameters: Dict[str, str] = None
    ) -> Dict:
        """
        Deploy to an environment
        
        Args:
            source_environment_id: Source environment ID
            target_environment_id: Target environment ID
            deployment_type: Type of deployment (full, incremental, rollback)
            parameters: Additional deployment parameters
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.DeployRequest(
            source_environment_id=source_environment_id,
            target_environment_id=target_environment_id,
            deployment_type=deployment_type,
            parameters=parameters or {}
        )
        
        response = self.stub.DeployToEnvironment(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'deployment_id': response.deployment_id
        }
    
    def get_deployment_status(self, deployment_id: str) -> Dict:
        """
        Get deployment status
        
        Args:
            deployment_id: Deployment ID
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.GetDeploymentStatusRequest(
            deployment_id=deployment_id
        )
        
        response = self.stub.GetDeploymentStatus(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'status': {
                'deployment_id': response.status.deployment_id,
                'status': response.status.status,
                'progress': response.status.progress,
                'current_step': response.status.current_step,
                'logs': list(response.status.logs),
                'started_at': response.status.started_at,
                'completed_at': response.status.completed_at
            } if response.HasField('status') else None
        }
    
    def rollback_deployment(
        self,
        deployment_id: str,
        reason: str = ""
    ) -> Dict:
        """
        Rollback a deployment
        
        Args:
            deployment_id: Deployment ID to rollback
            reason: Reason for rollback
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.RollbackRequest(
            deployment_id=deployment_id,
            reason=reason
        )
        
        response = self.stub.RollbackDeployment(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'rollback_id': response.rollback_id
        }
    
    # Environment variable management methods
    
    def set_environment_variable(
        self,
        environment_id: str,
        key: str,
        value: str,
        is_secret: bool = False
    ) -> Dict:
        """
        Set an environment variable
        
        Args:
            environment_id: Environment ID
            key: Variable key
            value: Variable value
            is_secret: Whether the variable is a secret
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.SetVariableRequest(
            environment_id=environment_id,
            key=key,
            value=value,
            is_secret=is_secret
        )
        
        response = self.stub.SetEnvironmentVariable(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'variable': {
                'key': response.variable.key,
                'value': response.variable.value,
                'is_secret': response.variable.is_secret,
                'updated_at': response.variable.updated_at
            } if response.HasField('variable') else None
        }
    
    def get_environment_variable(
        self,
        environment_id: str,
        key: str
    ) -> Dict:
        """
        Get an environment variable
        
        Args:
            environment_id: Environment ID
            key: Variable key
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.GetVariableRequest(
            environment_id=environment_id,
            key=key
        )
        
        response = self.stub.GetEnvironmentVariable(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'variable': {
                'key': response.variable.key,
                'value': response.variable.value,
                'is_secret': response.variable.is_secret,
                'updated_at': response.variable.updated_at
            } if response.HasField('variable') else None
        }
    
    def list_environment_variables(self, environment_id: str) -> Dict:
        """
        List all environment variables
        
        Args:
            environment_id: Environment ID
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.ListVariablesRequest(
            environment_id=environment_id
        )
        
        response = self.stub.ListEnvironmentVariables(request)
        
        variables = []
        for var in response.variables:
            variables.append({
                'key': var.key,
                'value': var.value,
                'is_secret': var.is_secret,
                'updated_at': var.updated_at
            })
        
        return {
            'success': response.success,
            'message': response.message,
            'variables': variables
        }
    
    def delete_environment_variable(
        self,
        environment_id: str,
        key: str
    ) -> Dict:
        """
        Delete an environment variable
        
        Args:
            environment_id: Environment ID
            key: Variable key
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.DeleteVariableRequest(
            environment_id=environment_id,
            key=key
        )
        
        response = self.stub.DeleteEnvironmentVariable(request)
        
        return {
            'success': response.success,
            'message': response.message
        }
    
    # Health check methods
    
    def health_check(self, environment_id: str) -> Dict:
        """
        Perform health check on environment
        
        Args:
            environment_id: Environment ID
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.HealthCheckRequest(
            environment_id=environment_id
        )
        
        response = self.stub.HealthCheck(request)
        
        checks = []
        for check in response.checks:
            checks.append({
                'check_name': check.check_name,
                'passed': check.passed,
                'message': check.message,
                'response_time_ms': check.response_time_ms
            })
        
        return {
            'success': response.success,
            'message': response.message,
            'is_healthy': response.is_healthy,
            'checks': checks
        }
    
    def get_environment_metrics(self, environment_id: str) -> Dict:
        """
        Get environment metrics
        
        Args:
            environment_id: Environment ID
            
        Returns:
            Response dictionary
        """
        request = environment_management_pb2.GetMetricsRequest(
            environment_id=environment_id
        )
        
        response = self.stub.GetEnvironmentMetrics(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'metrics': {
                'environment_id': response.metrics.environment_id,
                'cpu_usage_percent': response.metrics.cpu_usage_percent,
                'memory_usage_percent': response.metrics.memory_usage_percent,
                'active_connections': response.metrics.active_connections,
                'request_count': response.metrics.request_count,
                'error_rate': response.metrics.error_rate,
                'uptime_seconds': response.metrics.uptime_seconds
            } if response.HasField('metrics') else None
        }


# Context manager for automatic connection cleanup
class EnvironmentManagementClientContext:
    """Context manager for Environment Management Client"""
    
    def __init__(self, host: str = 'localhost', port: int = 50052):
        self.host = host
        self.port = port
        self.client = None
    
    def __enter__(self):
        self.client = EnvironmentManagementClient(self.host, self.port)
        return self.client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()
