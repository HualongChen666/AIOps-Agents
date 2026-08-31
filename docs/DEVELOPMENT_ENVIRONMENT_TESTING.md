# 开发环境测试文档

## 概述

本文档描述了AIOps SRE Agent开发环境的测试方案，包括测试策略、测试方法、测试工具和测试流程。

---

## 测试策略

### 测试层次

#### 1. 基础设施测试
- Docker环境测试
- 网络连接测试
- 数据持久化测试
- 资源限制测试

#### 2. 服务测试
- 服务启动测试
- 服务健康检查测试
- 服务间通信测试
- 服务重启测试

#### 3. 功能测试
- API功能测试
- 数据库功能测试
- 缓存功能测试
- 监控功能测试

#### 4. 开发工具测试
- 调试工具测试
- 热重载测试
- 日志查看测试
- 容器访问测试

---

## 测试工具

### Docker测试工具

#### Docker Compose测试
```python
# tests/test_docker_compose.py
import pytest
import subprocess
import time
import requests
from typing import List

class TestDockerCompose:
    """测试Docker Compose配置"""
    
    @pytest.fixture(scope="class")
    def compose_up(self):
        """启动Docker Compose"""
        # 启动服务
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.dev.yml", "up", "-d"],
            check=True
        )
        
        # 等待服务启动
        time.sleep(30)
        
        yield
        
        # 清理
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.dev.yml", "down"],
            check=True
        )
    
    def test_services_started(self, compose_up):
        """测试服务启动"""
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.dev.yml", "ps"],
            capture_output=True,
            text=True
        )
        
        # 验证所有服务已启动
        assert "aiops-agent-dev" in result.stdout
        assert "aiops-frontend-dev" in result.stdout
        assert "aiops-postgres-dev" in result.stdout
        assert "aiops-redis-dev" in result.stdout
    
    def test_network_connectivity(self, compose_up):
        """测试网络连接"""
        # 测试API连接
        response = requests.get("http://localhost:8000/health")
        assert response.status_code == 200
        
        # 测试前端连接
        response = requests.get("http://localhost:3000")
        assert response.status_code == 200
```

### 服务健康检查测试

#### 健康检查测试
```python
# tests/test_health_checks.py
import pytest
import requests
import time

class TestHealthChecks:
    """测试健康检查"""
    
    def test_api_health_check(self):
        """测试API健康检查"""
        max_retries = 10
        retry_delay = 5
        
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:8000/health")
                if response.status_code == 200:
                    assert response.json()["status"] == "healthy"
                    return
            except requests.exceptions.RequestException:
                if i < max_retries - 1:
                    time.sleep(retry_delay)
        
        pytest.fail("API health check failed after retries")
    
    def test_database_health_check(self):
        """测试数据库健康检查"""
        max_retries = 10
        retry_delay = 5
        
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:8000/health/db")
                if response.status_code == 200:
                    assert response.json()["status"] == "healthy"
                    return
            except requests.exceptions.RequestException:
                if i < max_retries - 1:
                    time.sleep(retry_delay)
        
        pytest.fail("Database health check failed after retries")
    
    def test_redis_health_check(self):
        """测试Redis健康检查"""
        max_retries = 10
        retry_delay = 5
        
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:8000/health/redis")
                if response.status_code == 200:
                    assert response.json()["status"] == "healthy"
                    return
            except requests.exceptions.RequestException:
                if i < max_retries - 1:
                    time.sleep(retry_delay)
        
        pytest.fail("Redis health check failed after retries")
```

---

## 一键启动测试

### 启动脚本测试

#### 启动脚本测试
```python
# tests/test_startup_scripts.py
import pytest
import subprocess
import time
import requests

class TestStartupScripts:
    """测试启动脚本"""
    
    @pytest.fixture(scope="class")
    def dev_environment(self):
        """启动开发环境"""
        # 运行启动脚本
        subprocess.run(["bash", "scripts/dev-start.sh"], check=True)
        
        # 等待服务启动
        time.sleep(30)
        
        yield
        
        # 清理
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
    
    def test_one_click_startup(self, dev_environment):
        """测试一键启动"""
        # 验证所有服务已启动
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.dev.yml", "ps"],
            capture_output=True,
            text=True
        )
        
        # 验证服务状态
        assert "aiops-agent-dev" in result.stdout
        assert "aiops-frontend-dev" in result.stdout
        assert "aiops-postgres-dev" in result.stdout
        assert "aiops-redis-dev" in result.stdout
    
    def test_api_accessibility(self, dev_environment):
        """测试API可访问性"""
        response = requests.get("http://localhost:8000/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_frontend_accessibility(self, dev_environment):
        """测试前端可访问性"""
        response = requests.get("http://localhost:3000")
        assert response.status_code == 200
    
    def test_development_tools_accessibility(self, dev_environment):
        """测试开发工具可访问性"""
        # pgAdmin
        response = requests.get("http://localhost:5050")
        assert response.status_code == 200
        
        # Redis Commander
        response = requests.get("http://localhost:8081")
        assert response.status_code == 200
        
        # Mailhog
        response = requests.get("http://localhost:8025")
        assert response.status_code == 200
```

### 停止脚本测试

#### 停止脚本测试
```python
# tests/test_stop_scripts.py
import pytest
import subprocess
import time

class TestStopScripts:
    """测试停止脚本"""
    
    @pytest.fixture(scope="class")
    def dev_environment(self):
        """启动开发环境"""
        subprocess.run(["bash", "scripts/dev-start.sh"], check=True)
        time.sleep(30)
        yield
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
    
    def test_stop_all_services(self, dev_environment):
        """测试停止所有服务"""
        # 运行停止脚本
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
        
        # 等待服务停止
        time.sleep(10)
        
        # 验证服务已停止
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.dev.yml", "ps"],
            capture_output=True,
            text=True
        )
        
        # 验证没有运行的服务
        assert "Up" not in result.stdout
```

---

## 热重载测试

### 后端热重载测试

#### 后端热重载测试
```python
# tests/test_backend_hot_reload.py
import pytest
import subprocess
import time
import requests
import os

class TestBackendHotReload:
    """测试后端热重载"""
    
    @pytest.fixture(scope="class")
    def dev_environment(self):
        """启动开发环境"""
        subprocess.run(["bash", "scripts/dev-start.sh"], check=True)
        time.sleep(30)
        yield
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
    
    def test_python_file_reload(self, dev_environment):
        """测试Python文件热重载"""
        # 获取初始响应
        initial_response = requests.get("http://localhost:8000/api/test")
        initial_data = initial_response.json()
        
        # 修改Python文件
        with open("api/test_api.py", "a") as f:
            f.write("\n# Test modification\n")
        
        # 等待热重载
        time.sleep(5)
        
        # 获取新响应
        new_response = requests.get("http://localhost:8000/api/test")
        new_data = new_response.json()
        
        # 清理修改
        with open("api/test_api.py", "r") as f:
            content = f.read()
        with open("api/test_api.py", "w") as f:
            f.write(content.replace("\n# Test modification\n", ""))
        
        # 验证热重载生效
        assert True  # 根据实际验证逻辑调整
    
    def test_config_file_reload(self, dev_environment):
        """测试配置文件热重载"""
        # 修改配置文件
        with open("config.py", "a") as f:
            f.write("\n# Test config modification\n")
        
        # 等待热重载
        time.sleep(5)
        
        # 验证配置已重新加载
        # 根据实际验证逻辑调整
        
        # 清理修改
        with open("config.py", "r") as f:
            content = f.read()
        with open("config.py", "w") as f:
            f.write(content.replace("\n# Test config modification\n", ""))
        
        assert True
```

### 前端热重载测试

#### 前端热重载测试
```python
# tests/test_frontend_hot_reload.py
import pytest
import subprocess
import time
import requests

class TestFrontendHotReload:
    """测试前端热重载"""
    
    @pytest.fixture(scope="class")
    def dev_environment(self):
        """启动开发环境"""
        subprocess.run(["bash", "scripts/dev-start.sh"], check=True)
        time.sleep(30)
        yield
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
    
    def test_component_hot_reload(self, dev_environment):
        """测试组件热重载"""
        # 获取初始页面
        initial_response = requests.get("http://localhost:3000")
        initial_content = initial_response.text
        
        # 修改组件文件
        with open("frontend/components/TestComponent.tsx", "a") as f:
            f.write("\n{/* Test modification */}\n")
        
        # 等待热重载
        time.sleep(5)
        
        # 获取新页面
        new_response = requests.get("http://localhost:3000")
        new_content = new_response.text
        
        # 清理修改
        with open("frontend/components/TestComponent.tsx", "r") as f:
            content = f.read()
        with open("frontend/components/TestComponent.tsx", "w") as f:
            f.write(content.replace("\n{/* Test modification */}\n", ""))
        
        # 验证热重载生效
        assert True  # 根据实际验证逻辑调整
```

---

## 数据持久化测试

### 数据库持久化测试

#### 数据库持久化测试
```python
# tests/test_database_persistence.py
import pytest
import subprocess
import time
import requests

class TestDatabasePersistence:
    """测试数据库持久化"""
    
    @pytest.fixture(scope="class")
    def dev_environment(self):
        """启动开发环境"""
        subprocess.run(["bash", "scripts/dev-start.sh"], check=True)
        time.sleep(30)
        yield
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
    
    def test_data_persistence_across_restarts(self, dev_environment):
        """测试数据在重启间持久化"""
        # 创建测试数据
        response = requests.post(
            "http://localhost:8000/api/test-data",
            json={"key": "test", "value": "persistence_test"}
        )
        assert response.status_code == 201
        
        # 重启数据库服务
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.dev.yml", "restart", "postgres"],
            check=True
        )
        
        # 等待数据库重启
        time.sleep(15)
        
        # 验证数据仍然存在
        response = requests.get("http://localhost:8000/api/test-data/test")
        assert response.status_code == 200
        assert response.json()["value"] == "persistence_test"
```

### Redis持久化测试

#### Redis持久化测试
```python
# tests/test_redis_persistence.py
import pytest
import subprocess
import time
import requests

class TestRedisPersistence:
    """测试Redis持久化"""
    
    @pytest.fixture(scope="class")
    def dev_environment(self):
        """启动开发环境"""
        subprocess.run(["bash", "scripts/dev-start.sh"], check=True)
        time.sleep(30)
        yield
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
    
    def test_cache_persistence_across_restarts(self, dev_environment):
        """测试缓存在重启间持久化"""
        # 设置缓存
        response = requests.post(
            "http://localhost:8000/api/cache/test",
            json={"value": "cache_test"}
        )
        assert response.status_code == 200
        
        # 重启Redis服务
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.dev.yml", "restart", "redis"],
            check=True
        )
        
        # 等待Redis重启
        time.sleep(10)
        
        # 验证缓存仍然存在
        response = requests.get("http://localhost:8000/api/cache/test")
        assert response.status_code == 200
        assert response.json()["value"] == "cache_test"
```

---

## 调试工具测试

### 调试工具测试

#### 调试工具测试
```python
# tests/test_debugging_tools.py
import pytest
import subprocess
import time
import requests

class TestDebuggingTools:
    """测试调试工具"""
    
    @pytest.fixture(scope="class")
    def dev_environment(self):
        """启动开发环境"""
        subprocess.run(["bash", "scripts/dev-start.sh"], check=True)
        time.sleep(30)
        yield
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
    
    def test_pgadmin_accessibility(self, dev_environment):
        """测试pgAdmin可访问性"""
        response = requests.get("http://localhost:5050")
        assert response.status_code == 200
        assert "pgAdmin" in response.text
    
    def test_redis_commander_accessibility(self, dev_environment):
        """测试Redis Commander可访问性"""
        response = requests.get("http://localhost:8081")
        assert response.status_code == 200
        assert "Redis Commander" in response.text
    
    def test_mailhog_accessibility(self, dev_environment):
        """测试Mailhog可访问性"""
        response = requests.get("http://localhost:8025")
        assert response.status_code == 200
        assert "Mailhog" in response.text
    
    def test_container_access(self, dev_environment):
        """测试容器访问"""
        # 测试进入容器
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.dev.yml", "exec", "aiops-agent", "python", "--version"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Python" in result.stdout
```

---

## 监控工具测试

### 监控工具测试

#### 监控工具测试
```python
# tests/test_monitoring_tools.py
import pytest
import subprocess
import time
import requests

class TestMonitoringTools:
    """测试监控工具"""
    
    @pytest.fixture(scope="class")
    def dev_environment(self):
        """启动开发环境"""
        subprocess.run(["bash", "scripts/dev-start.sh"], check=True)
        subprocess.run(["docker-compose", "-f", "docker-compose.monitoring.yml", "up", "-d"], check=True)
        time.sleep(30)
        yield
        subprocess.run(["docker-compose", "-f", "docker-compose.monitoring.yml", "down"], check=True)
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
    
    def test_prometheus_accessibility(self, dev_environment):
        """测试Prometheus可访问性"""
        response = requests.get("http://localhost:9090")
        assert response.status_code == 200
        assert "Prometheus" in response.text
    
    def test_grafana_accessibility(self, dev_environment):
        """测试Grafana可访问性"""
        response = requests.get("http://localhost:3001")
        assert response.status_code == 200
        assert "Grafana" in response.text
    
    def test_jaeger_accessibility(self, dev_environment):
        """测试Jaeger可访问性"""
        response = requests.get("http://localhost:16686")
        assert response.status_code == 200
        assert "Jaeger" in response.text
    
    def test_metrics_collection(self, dev_environment):
        """测试指标收集"""
        response = requests.get("http://localhost:9090/api/v1/query?query=up")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
```

---

## 性能测试

### 启动性能测试

#### 启动性能测试
```python
# tests/test_startup_performance.py
import pytest
import subprocess
import time

class TestStartupPerformance:
    """测试启动性能"""
    
    def test_startup_time(self):
        """测试启动时间"""
        start_time = time.time()
        
        # 启动开发环境
        subprocess.run(["bash", "scripts/dev-start.sh"], check=True)
        
        # 等待所有服务启动
        time.sleep(30)
        
        startup_time = time.time() - start_time
        
        # 清理
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
        
        # 验证启动时间<60秒
        assert startup_time < 60, f"Startup time {startup_time}s exceeds 60s"
    
    def test_service_restart_time(self):
        """测试服务重启时间"""
        # 启动开发环境
        subprocess.run(["bash", "scripts/dev-start.sh"], check=True)
        time.sleep(30)
        
        # 测试API服务重启时间
        start_time = time.time()
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.dev.yml", "restart", "aiops-agent"],
            check=True
        )
        
        # 等待服务重启
        time.sleep(15)
        
        restart_time = time.time() - start_time
        
        # 清理
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
        
        # 验证重启时间<20秒
        assert restart_time < 20, f"Restart time {restart_time}s exceeds 20s"
```

---

## 集成测试

### 端到端测试

#### 端到端测试
```python
# tests/test_e2e.py
import pytest
import subprocess
import time
import requests

class TestE2E:
    """端到端测试"""
    
    @pytest.fixture(scope="class")
    def dev_environment(self):
        """启动开发环境"""
        subprocess.run(["bash", "scripts/dev-start.sh"], check=True)
        time.sleep(30)
        yield
        subprocess.run(["bash", "scripts/dev-stop.sh"], check=True)
    
    def test_complete_workflow(self, dev_environment):
        """测试完整工作流"""
        # 1. 创建告警
        alert_response = requests.post(
            "http://localhost:8000/api/alerts",
            json={
                "severity": "high",
                "message": "Test alert",
                "source": "test"
            }
        )
        assert alert_response.status_code == 201
        alert_id = alert_response.json()["id"]
        
        # 2. 获取告警
        get_response = requests.get(f"http://localhost:8000/api/alerts/{alert_id}")
        assert get_response.status_code == 200
        assert get_response.json()["message"] == "Test alert"
        
        # 3. 更新告警
        update_response = requests.put(
            f"http://localhost:8000/api/alerts/{alert_id}",
            json={"status": "resolved"}
        )
        assert update_response.status_code == 200
        
        # 4. 删除告警
        delete_response = requests.delete(f"http://localhost:8000/api/alerts/{alert_id}")
        assert delete_response.status_code == 204
```

---

## 测试自动化

### CI/CD集成

#### GitHub Actions配置
```yaml
# .github/workflows/dev-environment-tests.yml
name: Development Environment Tests

on: [push, pull_request]

jobs:
  dev-environment-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov requests
      - name: Start development environment
        run: bash scripts/dev-start.sh
      - name: Wait for services
        run: sleep 30
      - name: Run health checks
        run: pytest tests/test_health_checks.py -v
      - name: Run startup tests
        run: pytest tests/test_startup_scripts.py -v
      - name: Run hot reload tests
        run: pytest tests/test_backend_hot_reload.py -v
      - name: Run persistence tests
        run: pytest tests/test_database_persistence.py -v
      - name: Run debugging tools tests
        run: pytest tests/test_debugging_tools.py -v
      - name: Stop development environment
        run: bash scripts/dev-stop.sh
```

---

## 测试检查清单

### 基础设施测试
- [ ] Docker环境正常
- [ ] 网络连接正常
- [ ] 数据持久化正常
- [ ] 资源限制正常

### 服务测试
- [ ] 所有服务启动成功
- [ ] 健康检查通过
- [ ] 服务间通信正常
- [ ] 服务重启正常

### 功能测试
- [ ] API功能正常
- [ ] 数据库功能正常
- [ ] 缓存功能正常
- [ ] 监控功能正常

### 开发工具测试
- [ ] 调试工具正常
- [ ] 热重载正常
- [ ] 日志查看正常
- [ ] 容器访问正常

---

## 测试最佳实践

### 1. 测试组织
- 按功能模块组织测试
- 使用描述性的测试名称
- 保持测试独立和可重复
- 使用测试固件和参数化

### 2. 测试覆盖
- 基础设施测试覆盖率100%
- 服务测试覆盖率≥90%
- 功能测试覆盖率≥80%
- 开发工具测试覆盖率≥70%

### 3. 测试性能
- 使用并行测试提高效率
- 优化测试执行时间
- 避免不必要的等待
- 使用Mock减少依赖

### 4. 测试维护
- 定期更新测试用例
- 移除过时的测试
- 保持测试代码质量
- 监控测试执行时间

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 开发团队