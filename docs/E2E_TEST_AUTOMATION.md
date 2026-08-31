# E2E测试自动化文档

## 概述

本文档描述了AIOps SRE Agent的E2E测试自动化方案，包括自动化执行流程、测试调度、测试监控和最佳实践。

---

## 自动化架构

### 自动化流程

```
┌─────────────────────────────────────────────────────────┐
│              E2E Test Automation Architecture            │
├─────────────────────────────────────────────────────────┤
│  1. Test Scheduling                                   │
│     ├── Cron scheduler                                │
│     ├── Event-based triggers                          │
│     ├── Manual triggers                                │
│     └── CI/CD triggers                                │
├─────────────────────────────────────────────────────────┤
│  2. Environment Setup                                 │
│     ├── Spin up test environment                     │
│     ├── Deploy latest code                             │
│     ├── Configure test data                           │
│     └── Verify environment health                     │
├─────────────────────────────────────────────────────────┤
│  3. Test Execution                                    │
│     ├── Run test suite                                 │
|     ├── Monitor test progress                         │
|     ├── Capture test results                           │
|     └── Handle test failures                           │
├─────────────────────────────────────────────────────────┤
│  4. Result Processing                                 │
│     ├── Generate test reports                          │
|     ├── Calculate metrics                              │
|     ├── Compare with baseline                          │
|     └── Store test results                            │
├─────────────────────────────────────────────────────────┤
│  5. Notification                                      │
│     ├── Send success notifications                      │
|     ├── Send failure notifications                      │
|     ├── Update status dashboards                        │
|     └── Trigger remediation actions                    │
├─────────────────────────────────────────────────────────┤
│  6. Environment Cleanup                               │
│     ├── Stop test services                             │
|     ├── Clean test data                                │
|     ├── Release resources                              │
│     └── Archive test artifacts                         │
└─────────────────────────────────────────────────────────┘
```

---

## 测试调度

### Cron调度

#### 定期测试调度
```yaml
# .github/workflows/scheduled-e2e.yml
name: Scheduled E2E Tests

on:
  schedule:
    # 每天凌晨2点运行
    - cron: '0 2 * * *'
    # 每周一上午9点运行
    - cron: '0 9 * * 1'
    # 每月1号凌晨3点运行
    - cron: '0 3 1 * *'
  workflow_dispatch:  # 允许手动触发

jobs:
  scheduled-e2e:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup environment
        run: |
          python -m pip install -r requirements.txt
          npx playwright install --with-deps
      
      - name: Start services
        run: |
          docker-compose -f docker-compose.test.yml up -d
          sleep 30
      
      - name: Run E2E tests
        run: npx playwright test
      
      - name: Generate report
        run: npx playwright show-report
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: scheduled-e2e-results
          path: playwright-report/
      
      - name: Cleanup
        if: always()
        run: docker-compose -f docker-compose.test.yml down
```

### 事件触发调度

#### Pull Request触发
```yaml
# .github/workflows/pr-e2e.yml
name: PR E2E Tests

on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main, develop]

jobs:
  pr-e2e:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup environment
        run: |
          python -m pip install -r requirements.txt
          npx playwright install --with-deps
      
      - name: Start services
        run: |
          docker-compose -f docker-compose.test.yml up -d
          sleep 30
      
      - name: Run E2E tests
        run: npx playwright test
      
      - name: Comment PR with results
        uses: actions/github-script@v6
        if: always()
        with:
          script: |
            const fs = require('fs');
            const results = fs.readFileSync('test-results/results.json', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `E2E Test Results:\n\`\`\`\n${results}\n\`\`\``
            });
      
      - name: Cleanup
        if: always()
        run: docker-compose -f docker-compose.test.yml down
```

### 手动触发调度

#### 手动触发配置
```yaml
# .github/workflows/manual-e2e.yml
name: Manual E2E Tests

on:
  workflow_dispatch:
    inputs:
      test_suite:
        description: 'Test suite to run'
        required: true
        type: choice
        options:
          - all
          - alert-processing
          - ai-analysis
          - auto-repair
      environment:
        description: 'Environment to test'
        required: true
        type: choice
        options:
          - development
          - staging
          - production

jobs:
  manual-e2e:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup environment
        run: |
          python -m pip install -r requirements.txt
          npx playwright install --with-deps
      
      - name: Start services
        run: |
          docker-compose -f docker-compose.${{ inputs.environment }}.yml up -d
          sleep 30
      
      - name: Run E2E tests
        run: |
          if [ "${{ inputs.test_suite }}" = "all" ]; then
            npx playwright test
          else
            npx playwright test ${{ inputs.test_suite }}.spec.ts
          fi
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: manual-e2e-results
          path: playwright-report/
      
      - name: Cleanup
        if: always()
        run: docker-compose -f docker-compose.${{ inputs.environment }}.yml down
```

---

## 测试监控

### 实时监控

#### 测试执行监控
```python
# scripts/monitor_test_execution.py
import requests
import time
from typing import Dict, Any

class TestMonitor:
    """测试执行监控器"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
    
    def monitor_test_execution(self, test_id: str) -> Dict[str, Any]:
        """监控测试执行"""
        while True:
            response = requests.get(f"{self.api_url}/tests/{test_id}")
            status = response.json()
            
            print(f"Test status: {status['status']}")
            print(f"Progress: {status['progress']}%")
            print(f"Passed: {status['passed']}")
            print(f"Failed: {status['failed']}")
            
            if status['status'] in ['completed', 'failed']:
                return status
            
            time.sleep(10)
    
    def get_test_results(self, test_id: str) -> Dict[str, Any]:
        """获取测试结果"""
        response = requests.get(f"{self.api_url}/tests/{test_id}/results")
        return response.json()

# 使用示例
if __name__ == "__main__":
    monitor = TestMonitor("http://localhost:8000/api")
    status = monitor.monitor_test_execution("test-001")
    results = monitor.get_test_results("test-001")
    print(f"Test results: {results}")
```

### 测试指标收集

#### 指标收集脚本
```python
# scripts/collect_test_metrics.py
import requests
import json
from typing import Dict, Any

def collect_test_metrics(test_results: Dict[str, Any]) -> Dict[str, Any]:
    """收集测试指标"""
    metrics = {
        "total_tests": test_results.get("total", 0),
        "passed_tests": test_results.get("passed", 0),
        "failed_tests": test_results.get("failed", 0),
        "skipped_tests": test_results.get("skipped", 0),
        "pass_rate": 0,
        "fail_rate": 0,
        "duration": test_results.get("duration", 0),
        "timestamp": test_results.get("timestamp", "")
    }
    
    if metrics["total_tests"] > 0:
        metrics["pass_rate"] = metrics["passed_tests"] / metrics["total_tests"] * 100
        metrics["fail_rate"] = metrics["failed_tests"] / metrics["total_tests"] * 100
    
    return metrics

def send_metrics_to_prometheus(metrics: Dict[str, Any]):
    """发送指标到Prometheus"""
    # 发送指标到Prometheus Pushgateway
    pass

# 使用示例
if __name__ == "__main__":
    test_results = {
        "total": 100,
        "passed": 95,
        "failed": 5,
        "skipped": 0,
        "duration": 300,
        "timestamp": "2026-08-31T00:00:00Z"
    }
    
    metrics = collect_test_metrics(test_results)
    print(f"Test metrics: {metrics}")
    send_metrics_to_prometheus(metrics)
```

---

## 测试报告自动化

### 报告生成

#### 自动报告生成
```python
# scripts/generate_test_report.py
import json
from typing import Dict, Any
from datetime import datetime

def generate_test_report(test_results: Dict[str, Any]) -> str:
    """生成测试报告"""
    report = f"""
# E2E Test Report

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Tests**: {test_results['total']}
**Passed**: {test_results['passed']}
**Failed**: {test_results['failed']}
**Skipped**: {test_results['skipped']}
**Pass Rate**: {test_results['pass_rate']:.2f}%
**Duration**: {test_results['duration']}s

## Test Results

### Passed Tests
{chr(10).join(f"- {test}" for test in test_results['passed_tests'])}

### Failed Tests
{chr(10).join(f"- {test}" for test in test_results['failed_tests'])}

## Recommendations
{generate_recommendations(test_results)}
"""
    return report

def generate_recommendations(test_results: Dict[str, Any]) -> str:
    """生成推荐"""
    recommendations = []
    
    if test_results['fail_rate'] > 5:
        recommendations.append("- 调查失败测试的根本原因")
    
    if test_results['duration'] > 600:
        recommendations.append("- 优化测试执行时间")
    
    if test_results['pass_rate'] < 95:
        recommendations.append("- 提高测试通过率")
    
    return chr(10).join(recommendations)

# 使用示例
if __name__ == "__main__":
    test_results = {
        "total": 100,
        "passed": 95,
        "failed": 5,
        "skipped": 0,
        "pass_rate": 95.0,
        "fail_rate": 5.0,
        "duration": 300,
        "passed_tests": ["test1", "test2"],
        "failed_tests": ["test3", "test4"]
    }
    
    report = generate_test_report(test_results)
    print(report)
    
    # 保存报告
    with open("test-report.md", "w") as f:
        f.write(report)
```

---

## 测试数据管理

### 测试数据准备

#### 自动数据准备
```python
# scripts/prepare_test_data.py
import subprocess
import time

def prepare_test_data():
    """准备测试数据"""
    print("Preparing test data...")
    
    # 启动数据库
    subprocess.run(["docker-compose", "up", "-d", "postgres"])
    time.sleep(10)
    
    # 运行数据迁移
    subprocess.run(["alembic", "upgrade", "head"])
    
    # 加载测试数据
    subprocess.run(["python", "scripts/load_test_data.py"])
    
    print("Test data prepared successfully")

def cleanup_test_data():
    """清理测试数据"""
    print("Cleaning up test data...")
    
    # 清理数据库
    subprocess.run(["python", "scripts/cleanup_test_data.py"])
    
    # 停止数据库
    subprocess.run(["docker-compose", "down"])
    
    print("Test data cleaned up successfully")

# 使用示例
if __name__ == "__main__":
    prepare_test_data()
    # 运行测试
    cleanup_test_data()
```

---

## 测试环境管理

### 环境自动化

#### 环境启动脚本
```bash
#!/bin/bash
# scripts/start_test_environment.sh

echo "Starting test environment..."

# 启动Docker服务
docker-compose -f docker-compose.test.yml up -d

# 等待服务启动
echo "Waiting for services to start..."
sleep 30

# 验证服务健康
echo "Verifying service health..."
curl -f http://localhost:8000/health || exit 1
curl -f http://localhost:5432 || exit 1
curl -f http://localhost:6379 || exit 1

echo "Test environment started successfully!"
```

#### 环境停止脚本
```bash
#!/bin/bash
# scripts/stop_test_environment.sh

echo "Stopping test environment..."

# 停止Docker服务
docker-compose -f docker-compose.test.yml down

# 清理数据卷
docker volume rm aiops-sre-agent_test-data

echo "Test environment stopped successfully!"
```

---

## 测试结果分析

### 趋势分析

#### 测试趋势分析
```python
# scripts/analyze_test_trends.py
import requests
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta

def get_test_history(days: int = 30) -> List[Dict[str, Any]]:
    """获取测试历史"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    history = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        response = requests.get(
            f"http://localhost:8000/api/test-results?date={date.strftime('%Y-%m-%d')}"
        )
        history.append(response.json())
    
    return history

def analyze_trends(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析测试趋势"""
    pass_rates = [h['pass_rate'] for h in history]
    durations = [h['duration'] for h in history]
    
    trends = {
        "average_pass_rate": sum(pass_rates) / len(pass_rates),
        "average_duration": sum(durations) / len(durations),
        "pass_rate_trend": "increasing" if pass_rates[-1] > pass_rates[0] else "decreasing",
        "duration_trend": "decreasing" if durations[-1] < durations[0] else "increasing"
    }
    
    return trends

# 使用示例
if __name__ == "__main__":
    history = get_test_history(30)
    trends = analyze_trends(history)
    print(f"Test trends: {trends}")
```

---

## 故障自动恢复

### 失败自动处理

#### 失败恢复脚本
```python
# scripts/handle_test_failures.py
import requests
from typing import Dict, Any

def handle_test_failures(failed_tests: List[str]) -> None:
    """处理测试失败"""
    for test in failed_tests:
        print(f"Handling failed test: {test}")
        
        # 分析失败原因
        failure_reason = analyze_failure(test)
        
        # 尝试自动恢复
        if failure_reason == "environment_issue":
            restart_environment()
        elif failure_reason == "data_issue":
            refresh_test_data()
        elif failure_reason == "flaky_test":
            retry_test(test)

def analyze_failure(test: str) -> str:
    """分析失败原因"""
    # 分析失败日志
    # 返回失败原因
    return "environment_issue"

def restart_environment():
    """重启测试环境"""
    print("Restarting test environment...")
    # 重启环境逻辑

def refresh_test_data():
    """刷新测试数据"""
    print("Refreshing test data...")
    # 刷新数据逻辑

def retry_test(test: str):
    """重试测试"""
    print(f"Retrying test: {test}")
    # 重试测试逻辑

# 使用示例
if __name__ == "__main__":
    failed_tests = ["test1", "test2"]
    handle_test_failures(failed_tests)
```

---

## 测试自动化最佳实践

### 1. 测试隔离
- 每个测试独立运行
- 不依赖测试执行顺序
- 使用测试数据清理

### 2. 环境一致性
- 使用Docker确保环境一致
- 使用版本控制管理环境配置
- 定期更新测试环境

### 3. 失败处理
- 设置合理的重试次数
- 提供详细的错误信息
- 自动处理常见失败

### 4. 性能优化
- 并行执行测试
- 使用缓存减少构建时间
- 优化测试执行时间

---

## 测试自动化监控

### 监控仪表板

#### Grafana仪表板配置
```json
{
  "dashboard": {
    "title": "E2E Test Automation",
    "panels": [
      {
        "title": "Test Pass Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "test_pass_rate"
          }
        ]
      },
      {
        "title": "Test Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "test_duration"
          }
        ]
      },
      {
        "title": "Test Failures",
        "type": "graph",
        "targets": [
          {
            "expr": "test_failures"
          }
        ]
      }
    ]
  }
}
```

---

## 测试自动化验证

### 自动化验证清单

#### 功能验证
- [ ] 测试调度正常工作
- [ ] 测试执行自动化正常
- [ ] 测试报告自动生成
- [ ] 测试结果自动存储

#### 性能验证
- [ ] 测试执行时间<30分钟
- [ ] 测试报告生成时间<5分钟
- [ ] 测试数据准备时间<10分钟

#### 稳定性验证
- [ ] 测试自动化成功率≥95%
- [ ] 无重复性故障
- [ ] 环境启动成功率≥99%

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent DevOps团队