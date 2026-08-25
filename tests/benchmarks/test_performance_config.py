# -*- coding: utf-8 -*-
"""
Tests for Performance Configuration System
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from tests.benchmarks.benchmark_base import PerformanceMetricType, PerformanceThreshold
from tests.benchmarks.performance_config import (
    BenchmarkConfig,
    EnvironmentConfig,
    PerformanceConfigManager,
    ThresholdConfig,
    get_config_manager,
    reset_config_manager,
)


class TestBenchmarkConfig:
    """Test BenchmarkConfig dataclass"""

    def test_benchmark_config_creation(self):
        """Test creating benchmark configuration"""
        config = BenchmarkConfig(
            name="test_benchmark",
            enabled=True,
            iterations=10,
            warmup_iterations=2,
            timeout=300.0,
            sample_interval=0.1,
            metadata={"description": "Test benchmark"},
        )

        assert config.name == "test_benchmark"
        assert config.enabled is True
        assert config.iterations == 10
        assert config.warmup_iterations == 2
        assert config.timeout == 300.0
        assert config.sample_interval == 0.1
        assert config.metadata == {"description": "Test benchmark"}

    def test_benchmark_config_defaults(self):
        """Test benchmark configuration with defaults"""
        config = BenchmarkConfig(name="test")

        assert config.name == "test"
        assert config.enabled is True
        assert config.iterations == 10
        assert config.warmup_iterations == 2
        assert config.timeout == 300.0
        assert config.sample_interval == 0.1
        assert config.metadata == {}

    def test_benchmark_config_to_dict(self):
        """Test converting benchmark config to dictionary"""
        config = BenchmarkConfig(name="test", iterations=5, metadata={"key": "value"})

        result = config.to_dict()

        assert result["name"] == "test"
        assert result["iterations"] == 5
        assert result["metadata"] == {"key": "value"}


class TestThresholdConfig:
    """Test ThresholdConfig dataclass"""

    def test_threshold_config_creation(self):
        """Test creating threshold configuration"""
        config = ThresholdConfig(
            metric_type="response_time",
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0,
            unit="seconds",
        )

        assert config.metric_type == "response_time"
        assert config.excellent == 0.1
        assert config.good == 0.5
        assert config.acceptable == 1.0
        assert config.warning == 2.0
        assert config.critical == 5.0
        assert config.unit == "seconds"

    def test_threshold_config_defaults(self):
        """Test threshold configuration with defaults"""
        config = ThresholdConfig(
            metric_type="cpu_usage",
            excellent=20.0,
            good=50.0,
            acceptable=70.0,
            warning=85.0,
            critical=95.0,
        )

        assert config.unit == "ms"

    def test_threshold_config_to_threshold(self):
        """Test converting to PerformanceThreshold"""
        config = ThresholdConfig(
            metric_type="response_time",
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0,
            unit="seconds",
        )

        threshold = config.to_threshold()

        assert isinstance(threshold, PerformanceThreshold)
        assert threshold.metric_type == PerformanceMetricType.RESPONSE_TIME
        assert threshold.excellent == 0.1
        assert threshold.unit == "seconds"

    def test_threshold_config_to_threshold_unknown_type(self):
        """Test converting unknown metric type"""
        config = ThresholdConfig(
            metric_type="unknown_metric",
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0,
        )

        threshold = config.to_threshold()

        # Should default to RESPONSE_TIME
        assert threshold.metric_type == PerformanceMetricType.RESPONSE_TIME

    def test_threshold_config_from_dict(self):
        """Test creating threshold config from dictionary"""
        data = {
            "metric_type": "throughput",
            "excellent": 1000.0,
            "good": 500.0,
            "acceptable": 100.0,
            "warning": 50.0,
            "critical": 10.0,
            "unit": "ops_per_second",
        }

        config = ThresholdConfig.from_dict(data)

        assert config.metric_type == "throughput"
        assert config.excellent == 1000.0
        assert config.unit == "ops_per_second"

    def test_threshold_config_to_dict(self):
        """Test converting threshold config to dictionary"""
        config = ThresholdConfig(
            metric_type="memory_usage",
            excellent=30.0,
            good=50.0,
            acceptable=70.0,
            warning=85.0,
            critical=95.0,
            unit="percent",
        )

        result = config.to_dict()

        assert result["metric_type"] == "memory_usage"
        assert result["excellent"] == 30.0
        assert result["unit"] == "percent"


class TestEnvironmentConfig:
    """Test EnvironmentConfig dataclass"""

    def test_environment_config_creation(self):
        """Test creating environment configuration"""
        benchmark_config = BenchmarkConfig(name="test_benchmark")
        threshold_config = ThresholdConfig(
            metric_type="response_time",
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0,
        )

        env_config = EnvironmentConfig(
            name="development",
            description="Development environment",
            benchmarks={"test_benchmark": benchmark_config},
            thresholds={"response_time": threshold_config},
            global_settings={"debug": True},
        )

        assert env_config.name == "development"
        assert env_config.description == "Development environment"
        assert len(env_config.benchmarks) == 1
        assert len(env_config.thresholds) == 1
        assert env_config.global_settings == {"debug": True}

    def test_environment_config_defaults(self):
        """Test environment configuration with defaults"""
        env_config = EnvironmentConfig(name="test")

        assert env_config.name == "test"
        assert env_config.description == ""
        assert env_config.benchmarks == {}
        assert env_config.thresholds == {}
        assert env_config.global_settings == {}

    def test_get_benchmark_config(self):
        """Test getting benchmark configuration"""
        benchmark_config = BenchmarkConfig(name="test_benchmark")
        env_config = EnvironmentConfig(name="test", benchmarks={"test_benchmark": benchmark_config})

        result = env_config.get_benchmark_config("test_benchmark")

        assert result is not None
        assert result.name == "test_benchmark"

    def test_get_benchmark_config_not_found(self):
        """Test getting non-existent benchmark configuration"""
        env_config = EnvironmentConfig(name="test")

        result = env_config.get_benchmark_config("nonexistent")

        assert result is None

    def test_get_threshold_config(self):
        """Test getting threshold configuration"""
        threshold_config = ThresholdConfig(
            metric_type="response_time",
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0,
        )
        env_config = EnvironmentConfig(name="test", thresholds={"response_time": threshold_config})

        result = env_config.get_threshold_config("response_time")

        assert result is not None
        assert result.metric_type == "response_time"

    def test_get_threshold_config_not_found(self):
        """Test getting non-existent threshold configuration"""
        env_config = EnvironmentConfig(name="test")

        result = env_config.get_threshold_config("nonexistent")

        assert result is None

    def test_add_benchmark_config(self):
        """Test adding benchmark configuration"""
        env_config = EnvironmentConfig(name="test")
        benchmark_config = BenchmarkConfig(name="new_benchmark")

        env_config.add_benchmark_config(benchmark_config)

        assert "new_benchmark" in env_config.benchmarks
        assert env_config.benchmarks["new_benchmark"].name == "new_benchmark"

    def test_add_threshold_config(self):
        """Test adding threshold configuration"""
        env_config = EnvironmentConfig(name="test")
        threshold_config = ThresholdConfig(
            metric_type="new_metric",
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0,
        )

        env_config.add_threshold_config(threshold_config)

        assert "new_metric" in env_config.thresholds
        assert env_config.thresholds["new_metric"].metric_type == "new_metric"

    def test_environment_config_to_dict(self):
        """Test converting environment config to dictionary"""
        benchmark_config = BenchmarkConfig(name="test_benchmark")
        threshold_config = ThresholdConfig(
            metric_type="response_time",
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0,
        )
        env_config = EnvironmentConfig(
            name="test",
            benchmarks={"test_benchmark": benchmark_config},
            thresholds={"response_time": threshold_config},
            global_settings={"debug": True},
        )

        result = env_config.to_dict()

        assert result["name"] == "test"
        assert "benchmarks" in result
        assert "thresholds" in result
        assert result["global_settings"] == {"debug": True}

    def test_environment_config_from_dict(self):
        """Test creating environment config from dictionary"""
        data = {
            "name": "test",
            "description": "Test environment",
            "benchmarks": {
                "test_benchmark": {"name": "test_benchmark", "enabled": True, "iterations": 10}
            },
            "thresholds": {
                "response_time": {
                    "metric_type": "response_time",
                    "excellent": 0.1,
                    "good": 0.5,
                    "acceptable": 1.0,
                    "warning": 2.0,
                    "critical": 5.0,
                }
            },
            "global_settings": {"debug": True},
        }

        env_config = EnvironmentConfig.from_dict(data)

        assert env_config.name == "test"
        assert env_config.description == "Test environment"
        assert len(env_config.benchmarks) == 1
        assert len(env_config.thresholds) == 1
        assert env_config.global_settings == {"debug": True}


class TestPerformanceConfigManager:
    """Test PerformanceConfigManager"""

    def test_manager_initialization(self):
        """Test manager initialization"""
        manager = PerformanceConfigManager()

        assert manager.config_dir is not None
        assert len(manager.environments) > 0
        assert "default" in manager.environments
        assert manager.current_environment == "development"

    def test_manager_initialization_with_custom_dir(self):
        """Test manager initialization with custom directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = PerformanceConfigManager(config_dir=temp_dir)

            assert manager.config_dir == Path(temp_dir)

    def test_load_default_config(self):
        """Test loading default configuration"""
        manager = PerformanceConfigManager()

        assert "default" in manager.environments
        default_env = manager.environments["default"]
        assert default_env.name == "default"
        assert len(default_env.thresholds) > 0

    def test_default_thresholds_exist(self):
        """Test that default thresholds are configured"""
        manager = PerformanceConfigManager()

        default_env = manager.environments["default"]

        assert "response_time" in default_env.thresholds
        assert "throughput" in default_env.thresholds
        assert "cpu_usage" in default_env.thresholds
        assert "memory_usage" in default_env.thresholds
        assert "error_rate" in default_env.thresholds

    def test_load_from_yaml_file(self):
        """Test loading configuration from YAML file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml_content = """
performance:
  name: test_env
  description: Test environment
  benchmarks:
    test_benchmark:
      name: test_benchmark
      enabled: true
      iterations: 5
  thresholds:
    response_time:
      metric_type: response_time
      excellent: 0.1
      good: 0.5
      acceptable: 1.0
      warning: 2.0
      critical: 5.0
  global_settings:
    debug: true
"""
            f.write(yaml_content)
            temp_path = f.name

        try:
            manager = PerformanceConfigManager()
            env_config = manager.load_from_file(temp_path, environment_name="test_env")

            assert env_config.name == "test_env"
            assert "test_benchmark" in env_config.benchmarks
            assert "response_time" in env_config.thresholds
            assert env_config.global_settings["debug"] is True
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_from_json_file(self):
        """Test loading configuration from JSON file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json_content = {
                "performance": {
                    "name": "test_env",
                    "description": "Test environment",
                    "benchmarks": {
                        "test_benchmark": {
                            "name": "test_benchmark",
                            "enabled": True,
                            "iterations": 5,
                        }
                    },
                    "thresholds": {
                        "response_time": {
                            "metric_type": "response_time",
                            "excellent": 0.1,
                            "good": 0.5,
                            "acceptable": 1.0,
                            "warning": 2.0,
                            "critical": 5.0,
                        }
                    },
                    "global_settings": {"debug": True},
                }
            }
            json.dump(json_content, f)
            temp_path = f.name

        try:
            manager = PerformanceConfigManager()
            env_config = manager.load_from_file(temp_path, environment_name="test_env")

            assert env_config.name == "test_env"
            assert "test_benchmark" in env_config.benchmarks
            assert "response_time" in env_config.thresholds
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_from_file_not_found(self):
        """Test loading from non-existent file"""
        manager = PerformanceConfigManager()

        with pytest.raises(FileNotFoundError):
            manager.load_from_file("/nonexistent/path/config.yaml")

    def test_load_from_file_unsupported_format(self):
        """Test loading from unsupported file format"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write("<config></config>")
            temp_path = f.name

        try:
            manager = PerformanceConfigManager()

            with pytest.raises(ValueError, match="Unsupported file format"):
                manager.load_from_file(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_from_directory(self):
        """Test loading all configurations from directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create YAML file
            yaml_path = Path(temp_dir) / "env1.yaml"
            with open(yaml_path, "w") as f:
                f.write("""
performance:
  name: env1
  thresholds:
    response_time:
      metric_type: response_time
      excellent: 0.1
      good: 0.5
      acceptable: 1.0
      warning: 2.0
      critical: 5.0
""")

            # Create JSON file
            json_path = Path(temp_dir) / "env2.json"
            with open(json_path, "w") as f:
                json.dump(
                    {
                        "performance": {
                            "name": "env2",
                            "thresholds": {
                                "cpu_usage": {
                                    "metric_type": "cpu_usage",
                                    "excellent": 20.0,
                                    "good": 50.0,
                                    "acceptable": 70.0,
                                    "warning": 85.0,
                                    "critical": 95.0,
                                }
                            },
                        }
                    },
                    f,
                )

            manager = PerformanceConfigManager()
            loaded = manager.load_from_directory(temp_dir)

            assert "env1" in loaded
            assert "env2" in loaded

    def test_load_from_directory_not_found(self):
        """Test loading from non-existent directory"""
        manager = PerformanceConfigManager()

        loaded = manager.load_from_directory("/nonexistent/directory")

        assert loaded == {}

    def test_set_environment(self):
        """Test setting current environment"""
        manager = PerformanceConfigManager()

        # Add a test environment
        test_env = EnvironmentConfig(name="test")
        manager.environments["test"] = test_env

        result = manager.set_environment("test")

        assert result is True
        assert manager.current_environment == "test"

    def test_set_environment_not_found(self):
        """Test setting non-existent environment"""
        manager = PerformanceConfigManager()

        result = manager.set_environment("nonexistent")

        assert result is False
        assert manager.current_environment == "development"

    def test_get_current_environment(self):
        """Test getting current environment"""
        manager = PerformanceConfigManager()

        env = manager.get_current_environment()

        assert env is not None
        # The current environment should be either 'default' or 'development'
        assert env.name in ["default", "development"]

    def test_get_environment(self):
        """Test getting specific environment"""
        manager = PerformanceConfigManager()

        test_env = EnvironmentConfig(name="test")
        manager.environments["test"] = test_env

        result = manager.get_environment("test")

        assert result is not None
        assert result.name == "test"

    def test_get_environment_not_found(self):
        """Test getting non-existent environment"""
        manager = PerformanceConfigManager()

        result = manager.get_environment("nonexistent")

        assert result is None

    def test_get_benchmark_config(self):
        """Test getting benchmark configuration"""
        manager = PerformanceConfigManager()

        benchmark_config = BenchmarkConfig(name="test_benchmark")
        manager.add_benchmark_config(benchmark_config, environment_name="default")

        result = manager.get_benchmark_config("test_benchmark", environment_name="default")

        assert result is not None
        assert result.name == "test_benchmark"

    def test_get_benchmark_config_default(self):
        """Test getting benchmark configuration with default"""
        manager = PerformanceConfigManager()

        result = manager.get_benchmark_config("nonexistent")

        assert result is not None
        assert result.name == "nonexistent"

    def test_get_threshold_config(self):
        """Test getting threshold configuration"""
        manager = PerformanceConfigManager()

        result = manager.get_threshold_config("response_time")

        assert result is not None
        assert result.metric_type == "response_time"

    def test_get_threshold_config_default(self):
        """Test getting threshold configuration with default"""
        manager = PerformanceConfigManager()

        result = manager.get_threshold_config("nonexistent")

        assert result is not None
        assert result.metric_type == "nonexistent"

    def test_get_all_thresholds(self):
        """Test getting all thresholds"""
        manager = PerformanceConfigManager()

        thresholds = manager.get_all_thresholds()

        assert len(thresholds) > 0
        assert all(isinstance(t, PerformanceThreshold) for t in thresholds.values())

    def test_add_benchmark_config(self):
        """Test adding benchmark configuration"""
        manager = PerformanceConfigManager()

        benchmark_config = BenchmarkConfig(name="new_benchmark")
        manager.add_benchmark_config(benchmark_config)

        assert "new_benchmark" in manager.environments[manager.current_environment].benchmarks

    def test_add_threshold_config(self):
        """Test adding threshold configuration"""
        manager = PerformanceConfigManager()

        threshold_config = ThresholdConfig(
            metric_type="new_metric",
            excellent=0.1,
            good=0.5,
            acceptable=1.0,
            warning=2.0,
            critical=5.0,
        )
        manager.add_threshold_config(threshold_config)

        assert "new_metric" in manager.environments[manager.current_environment].thresholds

    def test_save_to_file_yaml(self):
        """Test saving configuration to YAML file"""
        manager = PerformanceConfigManager()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = f.name

        try:
            saved_path = manager.save_to_file(temp_path, environment_name="default", format="yaml")

            assert Path(saved_path).exists()

            with open(saved_path, "r") as f:
                content = yaml.safe_load(f)
                assert "name" in content
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_save_to_file_json(self):
        """Test saving configuration to JSON file"""
        manager = PerformanceConfigManager()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            saved_path = manager.save_to_file(temp_path, environment_name="default", format="json")

            assert Path(saved_path).exists()

            with open(saved_path, "r") as f:
                content = json.load(f)
                assert "name" in content
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_save_to_file_unsupported_format(self):
        """Test saving with unsupported format"""
        manager = PerformanceConfigManager()

        with pytest.raises(ValueError, match="Unsupported format"):
            manager.save_to_file("test.xml", environment_name="default", format="xml")

    def test_save_to_file_environment_not_found(self):
        """Test saving non-existent environment"""
        manager = PerformanceConfigManager()

        with pytest.raises(ValueError, match="Environment .* not found"):
            manager.save_to_file("test.yaml", environment_name="nonexistent")

    def test_list_environments(self):
        """Test listing all environments"""
        manager = PerformanceConfigManager()

        environments = manager.list_environments()

        assert isinstance(environments, list)
        assert "default" in environments

    def test_validate_configuration_valid(self):
        """Test validating valid configuration"""
        manager = PerformanceConfigManager()

        result = manager.validate_configuration(environment_name="default")

        # Default configuration should be valid or have only warnings
        assert result["valid"] is True or len(result["errors"]) == 0

    def test_validate_configuration_invalid_thresholds(self):
        """Test validating configuration with invalid thresholds"""
        manager = PerformanceConfigManager()

        # Add invalid threshold
        threshold_config = ThresholdConfig(
            metric_type="test",
            excellent=10.0,
            good=5.0,  # Invalid: good < excellent
            acceptable=1.0,
            warning=0.5,
            critical=0.1,
        )
        manager.add_threshold_config(threshold_config)

        result = manager.validate_configuration()

        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_configuration_invalid_benchmark(self):
        """Test validating configuration with invalid benchmark"""
        manager = PerformanceConfigManager()

        # Add invalid benchmark
        benchmark_config = BenchmarkConfig(name="test", iterations=0)  # Invalid: iterations < 1
        manager.add_benchmark_config(benchmark_config)

        result = manager.validate_configuration()

        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_configuration_environment_not_found(self):
        """Test validating non-existent environment"""
        manager = PerformanceConfigManager()

        result = manager.validate_configuration(environment_name="nonexistent")

        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestGlobalConfigManager:
    """Test global configuration manager functions"""

    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns singleton"""
        reset_config_manager()

        manager1 = get_config_manager()
        manager2 = get_config_manager()

        assert manager1 is manager2

    def test_reset_config_manager(self):
        """Test resetting global configuration manager"""
        manager1 = get_config_manager()

        reset_config_manager()

        manager2 = get_config_manager()

        assert manager1 is not manager2

    def test_get_config_manager_after_reset(self):
        """Test getting config manager after reset"""
        reset_config_manager()

        manager = get_config_manager()

        assert manager is not None
        assert "default" in manager.environments
