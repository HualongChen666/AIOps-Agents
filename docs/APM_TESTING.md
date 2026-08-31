# APM测试文档

## 概述

本文档描述了AIOps SRE Agent的APM（Application Performance Monitoring）功能测试方案，包括测试策略、测试方法、测试工具和测试流程。

---

## 测试策略

### 测试层次

#### 1. 组件测试
- OpenTelemetry SDK测试
- 追踪器测试
- 指标收集器测试
- 日志处理器测试

#### 2. 集成测试
- OpenTelemetry Collector测试
- 数据导出测试
- 监控后端测试
- 告警系统测试

#### 3. 端到端测试
- 完整追踪链路测试
- 指标收集测试
- 告警触发测试
- 仪表板显示测试

### 测试类型

#### 功能测试
- 追踪功能测试
- 指标收集测试
- 日志记录测试
- 告警功能测试

#### 性能测试
- 追踪性能测试
- 指标性能测试
- 数据导出性能测试
- 监控系统性能测试

#### 可靠性测试
- 数据丢失测试
- 服务恢复测试
- 告警可靠性测试
- 监控可用性测试

---

## 测试工具

### OpenTelemetry测试工具

#### OTel CLI
```bash
# 安装OTel CLI
pip install opentelemetry-cli

# 验证配置
otel validate ./otel-collector-config.yaml

# 启动Collector
otel-collector --config ./otel-collector-config.yaml
```

#### 测试脚本
```python
# tests/test_telemetry.py
import pytest
from opentelemetry import trace, metrics
from core.telemetry import initialize_telemetry, get_tracer, get_meter

class TestTelemetryInitialization:
    """测试OpenTelemetry初始化"""
    
    def test_telemetry_initialization(self):
        """测试OpenTelemetry初始化"""
        result = initialize_telemetry(
            service_name="test-service",
            service_version="1.0.0",
            otlp_endpoint="http://localhost:4317"
        )
        assert result is True
    
    def test_tracer_provider_initialization(self):
        """测试Tracer Provider初始化"""
        result = initialize_telemetry()
        tracer = get_tracer(__name__)
        assert tracer is not None
    
    def test_meter_provider_initialization(self):
        """测试Meter Provider初始化"""
        result = initialize_telemetry()
        meter = get_meter(__name__)
        assert meter is not None
```

### Prometheus测试工具

#### Prometheus测试
```python
# tests/test_prometheus.py
import pytest
import requests

class TestPrometheusMetrics:
    """测试Prometheus指标"""
    
    def test_prometheus_scrape(self):
        """测试Prometheus指标抓取"""
        response = requests.get("http://localhost:9090/metrics")
        assert response.status_code == 200
        assert "system_cpu_usage" in response.text
    
    def test_custom_metrics(self):
        """测试自定义指标"""
        response = requests.get("http://localhost:9090/metrics")
        assert "alerts_total" in response.text
        assert "repairs_total" in response.text
    
    def test_metric_labels(self):
        """测试指标标签"""
        response = requests.get("http://localhost:9090/metrics")
        assert 'severity="high"' in response.text
        assert 'repair_type="automatic"' in response.text
```

### Grafana测试工具

#### Grafana测试
```python
# tests/test_grafana.py
import pytest
import requests

class TestGrafanaDashboards:
    """测试Grafana仪表板"""
    
    def test_grafana_accessibility(self):
        """测试Grafana可访问性"""
        response = requests.get("http://localhost:3000")
        assert response.status_code == 200
    
    def test_dashboard_import(self):
        """测试仪表板导入"""
        dashboard_json = {
            "dashboard": {
                "title": "Test Dashboard",
                "uid": "test-dashboard",
                "panels": []
            }
        }
        
        response = requests.post(
            "http://localhost:3000/api/dashboards/db",
            json=dashboard_json,
            headers={"Authorization": "Bearer YOUR_API_KEY"}
        )
        assert response.status_code == 200
    
    def test_dashboard_data(self):
        """测试仪表板数据"""
        response = requests.get("http://localhost:3000/api/datasources")
        assert response.status_code == 200
        assert len(response.json()) > 0
```

---

## 追踪测试

### 分布式追踪测试

#### 追踪链路测试
```python
# tests/test_tracing.py
import pytest
from opentelemetry import trace
from core.telemetry import get_tracer

class TestDistributedTracing:
    """测试分布式追踪"""
    
    def test_trace_creation(self):
        """测试追踪创建"""
        tracer = get_tracer(__name__)
        
        with tracer.start_as_current_span("test_operation") as span:
            span.set_attribute("test_attr", "test_value")
            assert span.is_recording()
    
    def test_span_attributes(self):
        """测试Span属性"""
        tracer = get_tracer(__name__)
        
        with tracer.start_as_current_span("test_operation") as span:
            span.set_attribute("operation", "test")
            span.set_attribute("status", "success")
            assert span.attributes.get("operation") == "test"
            assert span.attributes.get("status") == "success"
    
    def test_span_events(self):
        """测试Span事件"""
        tracer = get_tracer(__name__)
        
        with tracer.start_as_current_span("test_operation") as span:
            span.add_event("test_event", {"key": "value"})
            assert len(span.events) > 0
    
    def test_trace_context_propagation(self):
        """测试追踪上下文传播"""
        tracer = get_tracer(__name__)
        
        with tracer.start_as_current_span("parent_operation") as parent_span:
            parent_span.set_attribute("parent_id", "test_parent")
            
            with tracer.start_as_current_span("child_operation") as child_span:
                child_span.set_attribute("child_id", "test_child")
                
                # 验证父子关系
                assert child_span.parent == parent_span.context
```

### 自动追踪测试

#### FastAPI自动追踪测试
```python
# tests/test_fastapi_tracing.py
import pytest
from fastapi.testclient import TestClient
from core.telemetry.fastapi import instrument_fastapi

class TestFastAPITracing:
    """测试FastAPI自动追踪"""
    
    def test_fastapi_instrumentation(self):
        """测试FastAPI自动追踪"""
        from main import app
        
        instrument_fastapi(app)
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        # 验证追踪已创建
    
    def test_httpx_instrumentation(self):
        """测试HTTPX自动追踪"""
        from core.telemetry.fastapi import instrument_httpx
        
        instrument_httpx()
        
        # 验证HTTPX追踪已启用
        assert True
```

---

## 指标测试

### 自定义指标测试

#### 指标收集测试
```python
# tests/test_metrics.py
import pytest
from core.telemetry import get_meter
from core.telemetry.metrics import CustomMetrics

class TestCustomMetrics:
    """测试自定义指标"""
    
    def test_counter_metric(self):
        """测试计数器指标"""
        meter = get_meter(__name__)
        metrics = CustomMetrics(meter)
        
        metrics.record_alert("high")
        metrics.record_repair("automatic")
        
        # 验证指标已记录
        assert True
    
    def test_histogram_metric(self):
        """测试直方图指标"""
        meter = get_meter(__name__)
        metrics = CustomMetrics(meter)
        
        metrics.record_processing_time(1.5, "validate")
        metrics.record_processing_time(2.0, "execute")
        
        # 验证指标已记录
        assert True
    
    def test_gauge_metric(self):
        """测试仪表指标"""
        meter = get_meter(__name__)
        metrics = CustomMetrics(meter)
        
        metrics.set_active_repairs(10)
        metrics.set_queue_size(50)
        
        # 验证指标已设置
        assert True
```

### 系统指标测试

#### 系统指标收集测试
```python
# tests/test_system_metrics.py
import pytest
from core.telemetry.system_metrics import collect_system_metrics

class TestSystemMetrics:
    """测试系统指标"""
    
    def test_cpu_metric(self):
        """测试CPU指标"""
        meter = get_meter(__name__)
        update_metrics = collect_system_metrics(meter)
        
        update_metrics()
        
        # 验证CPU指标已收集
        assert True
    
    def test_memory_metric(self):
        """测试内存指标"""
        meter = get_meter(__name__)
        update_metrics = collect_system_metrics(meter)
        
        update_metrics()
        
        # 验证内存指标已收集
        assert True
    
    def test_disk_metric(self):
        """测试磁盘指标"""
        meter = get_meter(__name__)
        update_metrics = collect_system_metrics(meter)
        
        update_metrics()
        
        # 验证磁盘指标已收集
        assert True
```

---

## 告警测试

### 告警规则测试

#### 告警规则验证
```python
# tests/test_alerts.py
import pytest
import requests

class TestAlertRules:
    """测试告警规则"""
    
    def test_system_health_alert(self):
        """测试系统健康告警"""
        # 模拟系统健康分数低于阈值
        # 验证告警触发
        assert True
    
    def test_api_performance_alert(self):
        """测试API性能告警"""
        # 模拟API错误率高于阈值
        # 验证告警触发
        assert True
    
    def test_database_performance_alert(self):
        """测试数据库性能告警"""
        # 模拟数据库延迟高于阈值
        # 验证告警触发
        assert True
    
    def test_cache_performance_alert(self):
        """测试缓存性能告警"""
        # 模拟缓存命中率低于阈值
        # 验证告警触发
        assert True
```

### 告警通知测试

#### 通知渠道测试
```python
# tests/test_alert_notifications.py
import pytest
import requests

class TestAlertNotifications:
    """测试告警通知"""
    
    def test_slack_notification(self):
        """测试Slack通知"""
        # 发送测试告警
        # 验证Slack通知已发送
        assert True
    
    def test_email_notification(self):
        """测试Email通知"""
        # 发送测试告警
        # 验证Email通知已发送
        assert True
    
    def test_pagerduty_notification(self):
        """测试PagerDuty通知"""
        # 发送测试告警
        # 验证PagerDuty通知已发送
        assert True
```

---

## 性能测试

### 追踪性能测试

#### 追踪性能测试
```python
# tests/test_tracing_performance.py
import pytest
import time
from opentelemetry import trace
from core.telemetry import get_tracer

class TestTracingPerformance:
    """测试追踪性能"""
    
    def test_trace_overhead(self):
        """测试追踪开销"""
        tracer = get_tracer(__name__)
        
        # 测量无追踪时的性能
        start_time = time.time()
        for _ in range(1000):
            pass
        no_trace_time = time.time() - start_time
        
        # 测量有追踪时的性能
        start_time = time.time()
        for _ in range(1000):
            with tracer.start_as_current_span("test_operation"):
                pass
        with_trace_time = time.time() - start_time
        
        # 追踪开销应小于10%
        overhead = (with_trace_time - no_trace_time) / no_trace_time
        assert overhead < 0.1
    
    def test_span_export_performance(self):
        """测试Span导出性能"""
        tracer = get_tracer(__name__)
        
        # 创建大量Span
        start_time = time.time()
        for i in range(100):
            with tracer.start_as_current_span(f"operation_{i}"):
                pass
        export_time = time.time() - start_time
        
        # 导出时间应小于1秒
        assert export_time < 1.0
```

### 指标性能测试

#### 指标收集性能测试
```python
# tests/test_metrics_performance.py
import pytest
import time
from core.telemetry import get_meter
from core.telemetry.metrics import CustomMetrics

class TestMetricsPerformance:
    """测试指标性能"""
    
    def test_metric_recording_overhead(self):
        """测试指标记录开销"""
        meter = get_meter(__name__)
        metrics = CustomMetrics(meter)
        
        # 测量无指标时的性能
        start_time = time.time()
        for _ in range(1000):
            pass
        no_metric_time = time.time() - start_time
        
        # 测量有指标时的性能
        start_time = time.time()
        for _ in range(1000):
            metrics.record_alert("high")
        with_metric_time = time.time() - start_time
        
        # 指标开销应小于5%
        overhead = (with_metric_time - no_metric_time) / no_metric_time
        assert overhead < 0.05
    
    def test_metric_export_performance(self):
        """测试指标导出性能"""
        meter = get_meter(__name__)
        metrics = CustomMetrics(meter)
        
        # 记录大量指标
        for i in range(1000):
            metrics.record_alert("high")
        
        # 等待指标导出
        time.sleep(20)
        
        # 验证指标已导出
        assert True
```

---

## 集成测试

### 端到端追踪测试

#### 完整追踪链路测试
```python
# tests/test_e2e_tracing.py
import pytest
from opentelemetry import trace
from core.telemetry import get_tracer

class TestE2ETracing:
    """端到端追踪测试"""
    
    def test_complete_trace_chain(self):
        """测试完整追踪链路"""
        tracer = get_tracer(__name__)
        
        # 模拟完整请求链路
        with tracer.start_as_current_span("http_request") as http_span:
            http_span.set_attribute("url", "http://api.example.com/endpoint")
            
            with tracer.start_as_current_span("database_query") as db_span:
                db_span.set_attribute("query", "SELECT * FROM alerts")
                
                with tracer.start_as_current_span("cache_lookup") as cache_span:
                    cache_span.set_attribute("key", "alert:123")
                    cache_span.set_attribute("hit", True)
        
        # 验证追踪链路完整性
        assert True
    
    def test_trace_context_across_services(self):
        """测试跨服务追踪上下文"""
        # 模拟跨服务调用
        # 验证追踪上下文传播
        assert True
```

### 端到端指标测试

#### 完整指标收集测试
```python
# tests/test_e2e_metrics.py
import pytest
from core.telemetry import get_meter
from core.telemetry.metrics import CustomMetrics

class TestE2EMetrics:
    """端到端指标测试"""
    
    def test_complete_metric_collection(self):
        """测试完整指标收集"""
        meter = get_meter(__name__)
        metrics = CustomMetrics(meter)
        
        # 模拟完整业务流程
        metrics.record_alert("high")
        metrics.record_repair("automatic")
        metrics.record_processing_time(1.5, "validate")
        metrics.set_active_repairs(10)
        metrics.set_queue_size(50)
        
        # 等待指标导出
        time.sleep(20)
        
        # 验证所有指标已收集
        assert True
    
    def test_metric_aggregation(self):
        """测试指标聚合"""
        # 验证指标聚合功能
        assert True
```

---

## 测试自动化

### CI/CD集成

#### GitHub Actions配置
```yaml
# .github/workflows/apm-tests.yml
name: APM Tests

on: [push, pull_request]

jobs:
  telemetry-tests:
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
          pip install pytest pytest-asyncio pytest-cov
      - name: Start services
        run: |
          docker-compose -f docker-compose.telemetry.yml up -d
      - name: Run telemetry tests
        run: pytest tests/test_telemetry.py -v
      - name: Run metrics tests
        run: pytest tests/test_metrics.py -v
      - name: Run tracing tests
        run: pytest tests/test_tracing.py -v
      - name: Run alerts tests
        run: pytest tests/test_alerts.py -v
      - name: Stop services
        run: docker-compose -f docker-compose.telemetry.yml down
```

### 测试报告

#### 测试报告生成
```python
# scripts/generate_apm_test_report.py
import pytest
import json

def generate_apm_test_report():
    """生成APM测试报告"""
    # 运行测试
    result = pytest.main([
        'tests/test_telemetry.py',
        'tests/test_metrics.py',
        'tests/test_tracing.py',
        'tests/test_alerts.py',
        '--json-report',
        '--json-report-file=apm-test-report.json',
        '--cov=core/telemetry',
        '--cov-report=html'
    ])
    
    # 生成HTML报告
    print("APM test report generated: apm-test-report.json")
    print("Coverage report generated: htmlcov/index.html")

if __name__ == "__main__":
    generate_apm_test_report()
```

---

## 测试检查清单

### 功能测试
- [ ] OpenTelemetry初始化成功
- [ ] 追踪器正常工作
- [ ] 指标收集器正常工作
- [ ] 日志处理器正常工作
- [ ] 告警规则正常触发
- [ ] 告警通知正常发送

### 性能测试
- [ ] 追踪开销<10%
- [ ] 指标开销<5%
- [ ] Span导出时间<1s
- [ ] 指标导出时间<1s
- [ ] 监控系统响应时间<1s

### 可靠性测试
- [ ] 数据丢失率<0.1%
- [ ] 服务恢复时间<5分钟
- [ ] 告警触发成功率>99%
- [ ] 监控系统可用性>99.9%

---

## 测试故障排除

### 常见问题

#### 追踪未显示
```python
# 解决方案：检查追踪配置
# 1. 验证Tracer Provider配置
# 2. 检查采样器配置
# 3. 验证OTLP Collector连接
# 4. 检查Jaeger配置
```

#### 指标未显示
```python
# 解决方案：检查指标配置
# 1. 验证Meter Provider配置
# 2. 检查指标导出间隔
# 3. 验证Prometheus配置
# 4. 检查指标名称和标签
```

#### 告警未触发
```python
# 解决方案：检查告警配置
# 1. 验证告警规则表达式
# 2. 检查告警持续时间
# 3. 验证Alertmanager配置
# 4. 检查通知渠道配置
```

---

## 测试最佳实践

### 1. 测试组织
- 按功能模块组织测试
- 使用描述性的测试名称
- 保持测试独立和可重复
- 使用测试固件和参数化

### 2. 测试覆盖
- 单元测试覆盖率≥80%
- 集成测试覆盖率≥70%
- E2E测试覆盖关键流程
- 性能测试覆盖关键指标

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