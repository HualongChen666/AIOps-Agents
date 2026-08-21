# -*- coding: utf-8 -*-
"""
Performance Configuration System
=================================

Enterprise-level performance configuration management supporting:
- Performance threshold configuration
- Benchmark test configuration
- Environment-specific configuration
- YAML/JSON configuration file support
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from loguru import logger

from tests.benchmarks.benchmark_base import PerformanceMetricType, PerformanceThreshold


@dataclass
class BenchmarkConfig:
    """Configuration for a specific benchmark test"""
    
    name: str
    enabled: bool = True
    iterations: int = 10
    warmup_iterations: int = 2
    timeout: float = 300.0
    sample_interval: float = 0.1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ThresholdConfig:
    """Configuration for performance thresholds"""
    
    metric_type: str
    excellent: float
    good: float
    acceptable: float
    warning: float
    critical: float
    unit: str = "ms"
    
    def to_threshold(self) -> PerformanceThreshold:
        """Convert to PerformanceThreshold object"""
        try:
            metric_enum = PerformanceMetricType(self.metric_type)
        except ValueError:
            logger.warning(f"Unknown metric type: {self.metric_type}, defaulting to RESPONSE_TIME")
            metric_enum = PerformanceMetricType.RESPONSE_TIME
        
        return PerformanceThreshold(
            metric_type=metric_enum,
            excellent=self.excellent,
            good=self.good,
            acceptable=self.acceptable,
            warning=self.warning,
            critical=self.critical,
            unit=self.unit
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThresholdConfig':
        """Create from dictionary"""
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class EnvironmentConfig:
    """Environment-specific performance configuration"""
    
    name: str
    description: str = ""
    benchmarks: Dict[str, BenchmarkConfig] = field(default_factory=dict)
    thresholds: Dict[str, ThresholdConfig] = field(default_factory=dict)
    global_settings: Dict[str, Any] = field(default_factory=dict)
    
    def get_benchmark_config(self, benchmark_name: str) -> Optional[BenchmarkConfig]:
        """Get configuration for a specific benchmark"""
        return self.benchmarks.get(benchmark_name)
    
    def get_threshold_config(self, metric_name: str) -> Optional[ThresholdConfig]:
        """Get threshold configuration for a specific metric"""
        return self.thresholds.get(metric_name)
    
    def add_benchmark_config(self, config: BenchmarkConfig):
        """Add benchmark configuration"""
        self.benchmarks[config.name] = config
    
    def add_threshold_config(self, config: ThresholdConfig):
        """Add threshold configuration"""
        self.thresholds[config.metric_type] = config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "benchmarks": {k: v.to_dict() for k, v in self.benchmarks.items()},
            "thresholds": {k: v.to_dict() for k, v in self.thresholds.items()},
            "global_settings": self.global_settings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnvironmentConfig':
        """Create from dictionary"""
        benchmarks = {
            k: BenchmarkConfig(**v) if isinstance(v, dict) else v
            for k, v in data.get("benchmarks", {}).items()
        }
        thresholds = {
            k: ThresholdConfig.from_dict(v) if isinstance(v, dict) else v
            for k, v in data.get("thresholds", {}).items()
        }
        
        return cls(
            name=data.get("name", "default"),
            description=data.get("description", ""),
            benchmarks=benchmarks,
            thresholds=thresholds,
            global_settings=data.get("global_settings", {})
        )


class PerformanceConfigManager:
    """Manages performance configuration across environments"""
    
    DEFAULT_THRESHOLDS = {
        "response_time": ThresholdConfig(
            metric_type="response_time",
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0,
            unit="seconds"
        ),
        "throughput": ThresholdConfig(
            metric_type="throughput",
            excellent=10.0,
            good=50.0,
            acceptable=100.0,
            warning=500.0,
            critical=1000.0,
            unit="ops_per_second"
        ),
        "cpu_usage": ThresholdConfig(
            metric_type="cpu_usage",
            excellent=20.0,
            good=50.0,
            acceptable=70.0,
            warning=85.0,
            critical=95.0,
            unit="percent"
        ),
        "memory_usage": ThresholdConfig(
            metric_type="memory_usage",
            excellent=30.0,
            good=50.0,
            acceptable=70.0,
            warning=85.0,
            critical=95.0,
            unit="percent"
        ),
        "error_rate": ThresholdConfig(
            metric_type="error_rate",
            excellent=0.0,
            good=0.1,
            acceptable=1.0,
            warning=5.0,
            critical=10.0,
            unit="percent"
        )
    }
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Directory containing configuration files
        """
        if config_dir is None:
            # Default to config directory in project root
            project_root = Path(__file__).parent.parent
            config_dir = project_root / "config"
        
        self.config_dir = Path(config_dir)
        self.environments: Dict[str, EnvironmentConfig] = {}
        self.current_environment: str = "development"
        self._load_default_config()
    
    def _load_default_config(self):
        """Load default configuration"""
        # Create default environment
        default_env = EnvironmentConfig(
            name="default",
            description="Default performance configuration"
        )
        
        # Add default thresholds
        for name, threshold in self.DEFAULT_THRESHOLDS.items():
            default_env.add_threshold_config(threshold)
        
        self.environments["default"] = default_env
        logger.info("Loaded default performance configuration")
    
    def load_from_file(self, file_path: Union[str, Path], environment_name: Optional[str] = None) -> EnvironmentConfig:
        """
        Load configuration from file (YAML or JSON)
        
        Args:
            file_path: Path to configuration file
            environment_name: Optional name for the environment
            
        Returns:
            Loaded environment configuration
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        # Determine file format
        if file_path.suffix in ['.yaml', '.yml']:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        elif file_path.suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        # Extract performance configuration if present
        perf_config = data.get('performance', data)
        
        # Create environment config
        env_name = environment_name or perf_config.get('name', file_path.stem)
        env_config = EnvironmentConfig.from_dict(perf_config)
        env_config.name = env_name
        
        self.environments[env_name] = env_config
        logger.info(f"Loaded performance configuration from {file_path} for environment '{env_name}'")
        
        return env_config
    
    def load_from_directory(self, directory: Optional[Union[str, Path]] = None) -> Dict[str, EnvironmentConfig]:
        """
        Load all configuration files from directory
        
        Args:
            directory: Directory to load from (defaults to config_dir)
            
        Returns:
            Dictionary of loaded environment configurations
        """
        if directory is None:
            directory = self.config_dir
        
        directory = Path(directory)
        
        if not directory.exists():
            logger.warning(f"Configuration directory not found: {directory}")
            return {}
        
        loaded = {}
        
        # Load YAML files
        for yaml_file in directory.glob('*.yaml'):
            try:
                env_name = yaml_file.stem
                env_config = self.load_from_file(yaml_file, env_name)
                loaded[env_name] = env_config
            except Exception as e:
                logger.error(f"Error loading {yaml_file}: {e}")
        
        # Load YML files
        for yml_file in directory.glob('*.yml'):
            try:
                env_name = yml_file.stem
                env_config = self.load_from_file(yml_file, env_name)
                loaded[env_name] = env_config
            except Exception as e:
                logger.error(f"Error loading {yml_file}: {e}")
        
        # Load JSON files
        for json_file in directory.glob('*.json'):
            try:
                env_name = json_file.stem
                env_config = self.load_from_file(json_file, env_name)
                loaded[env_name] = env_config
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")
        
        logger.info(f"Loaded {len(loaded)} configuration files from {directory}")
        return loaded
    
    def set_environment(self, environment_name: str) -> bool:
        """
        Set current environment
        
        Args:
            environment_name: Name of environment to set
            
        Returns:
            True if successful, False otherwise
        """
        if environment_name not in self.environments:
            logger.warning(f"Environment '{environment_name}' not found")
            return False
        
        self.current_environment = environment_name
        logger.info(f"Set current environment to '{environment_name}'")
        return True
    
    def get_current_environment(self) -> EnvironmentConfig:
        """Get current environment configuration"""
        return self.environments.get(self.current_environment, self.environments["default"])
    
    def get_environment(self, environment_name: str) -> Optional[EnvironmentConfig]:
        """Get specific environment configuration"""
        return self.environments.get(environment_name)
    
    def get_benchmark_config(self, benchmark_name: str, environment_name: Optional[str] = None) -> BenchmarkConfig:
        """
        Get benchmark configuration
        
        Args:
            benchmark_name: Name of benchmark
            environment_name: Optional environment name (uses current if not specified)
            
        Returns:
            Benchmark configuration
        """
        env_name = environment_name or self.current_environment
        env = self.environments.get(env_name, self.environments["default"])
        
        config = env.get_benchmark_config(benchmark_name)
        if config is None:
            # Return default config
            logger.debug(f"No config found for benchmark '{benchmark_name}', using default")
            return BenchmarkConfig(name=benchmark_name)
        
        return config
    
    def get_threshold_config(self, metric_name: str, environment_name: Optional[str] = None) -> ThresholdConfig:
        """
        Get threshold configuration
        
        Args:
            metric_name: Name of metric
            environment_name: Optional environment name (uses current if not specified)
            
        Returns:
            Threshold configuration
        """
        env_name = environment_name or self.current_environment
        env = self.environments.get(env_name, self.environments["default"])
        
        config = env.get_threshold_config(metric_name)
        if config is None:
            # Return default threshold if available
            if metric_name in self.DEFAULT_THRESHOLDS:
                logger.debug(f"No threshold found for metric '{metric_name}', using default")
                return self.DEFAULT_THRESHOLDS[metric_name]
            else:
                logger.warning(f"No threshold found for metric '{metric_name}'")
                # Return a conservative default
                return ThresholdConfig(
                    metric_type=metric_name,
                    excellent=0.0,
                    good=0.0,
                    acceptable=0.0,
                    warning=0.0,
                    critical=0.0,
                    unit="unknown"
                )
        
        return config
    
    def get_all_thresholds(self, environment_name: Optional[str] = None) -> Dict[str, PerformanceThreshold]:
        """
        Get all thresholds as PerformanceThreshold objects
        
        Args:
            environment_name: Optional environment name
            
        Returns:
            Dictionary of metric names to PerformanceThreshold objects
        """
        env_name = environment_name or self.current_environment
        env = self.environments.get(env_name, self.environments["default"])
        
        thresholds = {}
        for name, config in env.thresholds.items():
            thresholds[name] = config.to_threshold()
        
        # Add any missing defaults
        for name, default_config in self.DEFAULT_THRESHOLDS.items():
            if name not in thresholds:
                thresholds[name] = default_config.to_threshold()
        
        return thresholds
    
    def add_benchmark_config(self, config: BenchmarkConfig, environment_name: Optional[str] = None):
        """
        Add benchmark configuration
        
        Args:
            config: Benchmark configuration to add
            environment_name: Optional environment name
        """
        env_name = environment_name or self.current_environment
        if env_name not in self.environments:
            self.environments[env_name] = EnvironmentConfig(name=env_name)
        
        self.environments[env_name].add_benchmark_config(config)
        logger.info(f"Added benchmark config '{config.name}' to environment '{env_name}'")
    
    def add_threshold_config(self, config: ThresholdConfig, environment_name: Optional[str] = None):
        """
        Add threshold configuration
        
        Args:
            config: Threshold configuration to add
            environment_name: Optional environment name
        """
        env_name = environment_name or self.current_environment
        if env_name not in self.environments:
            self.environments[env_name] = EnvironmentConfig(name=env_name)
        
        self.environments[env_name].add_threshold_config(config)
        logger.info(f"Added threshold config for metric '{config.metric_type}' to environment '{env_name}'")
    
    def save_to_file(self, file_path: Union[str, Path], environment_name: Optional[str] = None, 
                    format: str = "yaml") -> str:
        """
        Save configuration to file
        
        Args:
            file_path: Path to save configuration
            environment_name: Optional environment name (uses current if not specified)
            format: File format ('yaml' or 'json')
            
        Returns:
            Path to saved file
        """
        env_name = environment_name or self.current_environment
        env = self.environments.get(env_name)
        
        if env is None:
            raise ValueError(f"Environment '{env_name}' not found")
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = env.to_dict()
        
        if format == "yaml":
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        elif format == "json":
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Saved configuration to {file_path}")
        return str(file_path)
    
    def list_environments(self) -> List[str]:
        """List all available environments"""
        return list(self.environments.keys())
    
    def validate_configuration(self, environment_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate configuration for an environment
        
        Args:
            environment_name: Optional environment name
            
        Returns:
            Validation result with errors and warnings
        """
        env_name = environment_name or self.current_environment
        env = self.environments.get(env_name)
        
        if env is None:
            return {
                "valid": False,
                "errors": [f"Environment '{env_name}' not found"],
                "warnings": []
            }
        
        errors = []
        warnings = []
        
        # Validate thresholds
        for name, threshold in env.thresholds.items():
            if threshold.critical <= threshold.warning:
                errors.append(f"Threshold '{name}': critical value must be greater than warning")
            if threshold.warning <= threshold.acceptable:
                errors.append(f"Threshold '{name}': warning value must be greater than acceptable")
            if threshold.acceptable <= threshold.good:
                errors.append(f"Threshold '{name}': acceptable value must be greater than good")
            if threshold.good <= threshold.excellent:
                errors.append(f"Threshold '{name}': good value must be greater than excellent")
            
            if threshold.critical < 0:
                warnings.append(f"Threshold '{name}': negative critical value")
        
        # Validate benchmark configs
        for name, benchmark in env.benchmarks.items():
            if benchmark.iterations < 1:
                errors.append(f"Benchmark '{name}': iterations must be at least 1")
            if benchmark.warmup_iterations < 0:
                errors.append(f"Benchmark '{name}': warmup_iterations cannot be negative")
            if benchmark.timeout < 0:
                errors.append(f"Benchmark '{name}': timeout cannot be negative")
            if benchmark.sample_interval <= 0:
                errors.append(f"Benchmark '{name}': sample_interval must be positive")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


# Global configuration manager instance
_global_config_manager: Optional[PerformanceConfigManager] = None


def get_config_manager() -> PerformanceConfigManager:
    """Get global configuration manager instance"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = PerformanceConfigManager()
    return _global_config_manager


def reset_config_manager():
    """Reset global configuration manager instance"""
    global _global_config_manager
    _global_config_manager = None
