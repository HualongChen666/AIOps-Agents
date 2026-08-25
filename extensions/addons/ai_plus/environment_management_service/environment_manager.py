"""
Environment Manager - Core environment management logic
"""

import json
import os
import uuid
import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import shutil


@dataclass
class Environment:
    """Environment data model"""
    id: str
    name: str
    type: str  # dev, staging, prod
    config: Dict[str, str]
    description: str
    status: str  # active, inactive, error
    created_at: int
    updated_at: int
    variables: Dict[str, Dict[str, Any]]  # key -> {value, is_secret, updated_at}
    
    def to_dict(self) -> Dict:
        return asdict(self)


class EnvironmentManager:
    """Manages multiple environments with isolation and configuration"""
    
    VALID_ENV_TYPES = ['dev', 'staging', 'prod']
    VALID_STATUSES = ['active', 'inactive', 'error']
    
    def __init__(self, storage_path: str = None):
        """
        Initialize the environment manager
        
        Args:
            storage_path: Path to store environment data
        """
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(__file__), 
                'data', 
                'environments'
            )
        
        self.storage_path = storage_path
        self.environments: Dict[str, Environment] = {}
        self.lock = threading.RLock()
        
        # Create storage directory
        os.makedirs(storage_path, exist_ok=True)
        
        # Load existing environments
        self._load_environments()
        
        # Initialize default environments if none exist
        if not self.environments:
            self._initialize_default_environments()
    
    def _load_environments(self):
        """Load environments from storage"""
        try:
            if os.path.exists(self.storage_path):
                for filename in os.listdir(self.storage_path):
                    if filename.endswith('.json'):
                        filepath = os.path.join(self.storage_path, filename)
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            env = Environment(**data)
                            self.environments[env.id] = env
        except Exception as e:
            print(f"Error loading environments: {e}")
    
    def _save_environment(self, environment: Environment):
        """Save environment to storage"""
        try:
            filepath = os.path.join(self.storage_path, f"{environment.id}.json")
            with open(filepath, 'w') as f:
                json.dump(environment.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving environment: {e}")
            raise
    
    def _initialize_default_environments(self):
        """Initialize default dev, staging, and prod environments"""
        default_configs = {
            'dev': {
                'log_level': 'DEBUG',
                'max_connections': '100',
                'timeout': '30',
                'feature_flags': 'all'
            },
            'staging': {
                'log_level': 'INFO',
                'max_connections': '500',
                'timeout': '60',
                'feature_flags': 'beta'
            },
            'prod': {
                'log_level': 'WARNING',
                'max_connections': '1000',
                'timeout': '120',
                'feature_flags': 'stable'
            }
        }
        
        for env_type, config in default_configs.items():
            env = Environment(
                id=str(uuid.uuid4()),
                name=f"{env_type.capitalize()} Environment",
                type=env_type,
                config=config,
                description=f"Default {env_type} environment",
                status='active',
                created_at=int(time.time()),
                updated_at=int(time.time()),
                variables={}
            )
            self.environments[env.id] = env
            self._save_environment(env)
    
    def create_environment(
        self, 
        name: str, 
        env_type: str, 
        config: Dict[str, str],
        description: str = ""
    ) -> Environment:
        """
        Create a new environment
        
        Args:
            name: Environment name
            env_type: Environment type (dev, staging, prod)
            config: Configuration dictionary
            description: Environment description
            
        Returns:
            Created environment
            
        Raises:
            ValueError: If validation fails
        """
        with self.lock:
            # Validate environment type
            if env_type not in self.VALID_ENV_TYPES:
                raise ValueError(
                    f"Invalid environment type: {env_type}. "
                    f"Must be one of {self.VALID_ENV_TYPES}"
                )
            
            # Check for duplicate names
            for env in self.environments.values():
                if env.name == name:
                    raise ValueError(f"Environment with name '{name}' already exists")
            
            # Create environment
            env = Environment(
                id=str(uuid.uuid4()),
                name=name,
                type=env_type,
                config=config.copy(),
                description=description,
                status='active',
                created_at=int(time.time()),
                updated_at=int(time.time()),
                variables={}
            )
            
            self.environments[env.id] = env
            self._save_environment(env)
            
            return env
    
    def get_environment(self, environment_id: str) -> Optional[Environment]:
        """
        Get environment by ID
        
        Args:
            environment_id: Environment ID
            
        Returns:
            Environment or None if not found
        """
        with self.lock:
            return self.environments.get(environment_id)
    
    def list_environments(
        self, 
        env_type: str = None, 
        status: str = None
    ) -> List[Environment]:
        """
        List environments with optional filters
        
        Args:
            env_type: Filter by environment type
            status: Filter by status
            
        Returns:
            List of environments
        """
        with self.lock:
            environments = list(self.environments.values())
            
            if env_type:
                environments = [e for e in environments if e.type == env_type]
            
            if status:
                environments = [e for e in environments if e.status == status]
            
            return environments
    
    def update_environment(
        self, 
        environment_id: str, 
        config: Dict[str, str] = None,
        description: str = None
    ) -> Environment:
        """
        Update environment configuration
        
        Args:
            environment_id: Environment ID
            config: New configuration (partial update)
            description: New description
            
        Returns:
            Updated environment
            
        Raises:
            ValueError: If environment not found
        """
        with self.lock:
            env = self.environments.get(environment_id)
            if not env:
                raise ValueError(f"Environment {environment_id} not found")
            
            if config:
                env.config.update(config)
            
            if description is not None:
                env.description = description
            
            env.updated_at = int(time.time())
            self._save_environment(env)
            
            return env
    
    def delete_environment(self, environment_id: str) -> bool:
        """
        Delete an environment
        
        Args:
            environment_id: Environment ID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If trying to delete a default environment
        """
        with self.lock:
            env = self.environments.get(environment_id)
            if not env:
                return False
            
            # Prevent deletion of default environments
            if env.name in ['Dev Environment', 'Staging Environment', 'Prod Environment']:
                raise ValueError("Cannot delete default environments")
            
            # Remove from memory
            del self.environments[environment_id]
            
            # Remove from storage
            filepath = os.path.join(self.storage_path, f"{environment_id}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return True
    
    def set_variable(
        self, 
        environment_id: str, 
        key: str, 
        value: str,
        is_secret: bool = False
    ) -> Environment:
        """
        Set an environment variable
        
        Args:
            environment_id: Environment ID
            key: Variable key
            value: Variable value
            is_secret: Whether the variable is a secret
            
        Returns:
            Updated environment
            
        Raises:
            ValueError: If environment not found
        """
        with self.lock:
            env = self.environments.get(environment_id)
            if not env:
                raise ValueError(f"Environment {environment_id} not found")
            
            env.variables[key] = {
                'value': value,
                'is_secret': is_secret,
                'updated_at': int(time.time())
            }
            
            env.updated_at = int(time.time())
            self._save_environment(env)
            
            return env
    
    def get_variable(
        self, 
        environment_id: str, 
        key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get an environment variable
        
        Args:
            environment_id: Environment ID
            key: Variable key
            
        Returns:
            Variable data or None if not found
        """
        with self.lock:
            env = self.environments.get(environment_id)
            if not env:
                return None
            
            return env.variables.get(key)
    
    def list_variables(self, environment_id: str) -> Dict[str, Dict[str, Any]]:
        """
        List all environment variables
        
        Args:
            environment_id: Environment ID
            
        Returns:
            Dictionary of variables
        """
        with self.lock:
            env = self.environments.get(environment_id)
            if not env:
                return {}
            
            return env.variables.copy()
    
    def delete_variable(
        self, 
        environment_id: str, 
        key: str
    ) -> Environment:
        """
        Delete an environment variable
        
        Args:
            environment_id: Environment ID
            key: Variable key
            
        Returns:
            Updated environment
            
        Raises:
            ValueError: If environment not found
        """
        with self.lock:
            env = self.environments.get(environment_id)
            if not env:
                raise ValueError(f"Environment {environment_id} not found")
            
            if key in env.variables:
                del env.variables[key]
                env.updated_at = int(time.time())
                self._save_environment(env)
            
            return env
    
    def get_config(self, environment_id: str) -> Optional[Dict[str, str]]:
        """
        Get environment configuration
        
        Args:
            environment_id: Environment ID
            
        Returns:
            Configuration dictionary or None if not found
        """
        with self.lock:
            env = self.environments.get(environment_id)
            if not env:
                return None
            
            return env.config.copy()
    
    def update_config(
        self, 
        environment_id: str, 
        config: Dict[str, str]
    ) -> Environment:
        """
        Update environment configuration
        
        Args:
            environment_id: Environment ID
            config: New configuration (partial update)
            
        Returns:
            Updated environment
            
        Raises:
            ValueError: If environment not found
        """
        with self.lock:
            env = self.environments.get(environment_id)
            if not env:
                raise ValueError(f"Environment {environment_id} not found")
            
            env.config.update(config)
            env.updated_at = int(time.time())
            self._save_environment(env)
            
            return env
    
    def set_status(self, environment_id: str, status: str) -> Environment:
        """
        Set environment status
        
        Args:
            environment_id: Environment ID
            status: New status
            
        Returns:
            Updated environment
            
        Raises:
            ValueError: If environment not found or status invalid
        """
        with self.lock:
            if status not in self.VALID_STATUSES:
                raise ValueError(
                    f"Invalid status: {status}. "
                    f"Must be one of {self.VALID_STATUSES}"
                )
            
            env = self.environments.get(environment_id)
            if not env:
                raise ValueError(f"Environment {environment_id} not found")
            
            env.status = status
            env.updated_at = int(time.time())
            self._save_environment(env)
            
            return env
    
    def validate_isolation(self, environment_id: str) -> bool:
        """
        Validate environment isolation
        
        Args:
            environment_id: Environment ID
            
        Returns:
            True if isolation is valid
        """
        with self.lock:
            env = self.environments.get(environment_id)
            if not env:
                return False
            
            # Check for cross-environment references
            for other_env in self.environments.values():
                if other_env.id != environment_id:
                    # Check if config references other environment
                    for value in env.config.values():
                        if other_env.id in value or other_env.name in value:
                            return False
            
            return True
    
    def get_environment_hash(self, environment_id: str) -> str:
        """
        Get a hash of the environment state for comparison
        
        Args:
            environment_id: Environment ID
            
        Returns:
            MD5 hash of environment state
        """
        with self.lock:
            env = self.environments.get(environment_id)
            if not env:
                return ""
            
            # Create a deterministic string representation
            state_str = json.dumps(env.to_dict(), sort_keys=True)
            return hashlib.md5(state_str.encode()).hexdigest()
