# AIOps Agent API性能测试

## 概述

本目录包含AIOps Agent的API性能测试框架，基于Locust实现，支持多种测试场景和负载模式。

## 目录结构

```
tests/performance/
├── __init__.py              # 包初始化文件
├── locustfile.py            # Locust测试文件（包含65+ API端点）
├── locust_config.py         # 负载测试配置（不同测试场景）
├── report_generator.py      # 报告生成器（HTML/JSON）
├── run_performance_test.py  # 命令行运行脚本
├── reports/                 # 测试报告输出目录
└── README.md               # 本文档
```

## 测试覆盖的API端点

### 核心端点（高频访问）
- `/health` - 健康检查
- `/api/v1/alerts` - 告警列表
- `/api/v1/alerts/{id}` - 告警详情
- `/api/v1/metrics/summary` - 指标摘要
- `/api/v1/topology` - 拓扑查询

### AI相关端点
- `/api/v1/ai/inference` - AI推理
- `/api/v1/ai/rag/retrieve` - RAG检索
- `/api/v1/ai/feedback` - AI反馈

### 自动修复端点
- `/api/v1/autoheal/execute` - 自动修复执行
- `/api/v1/repairs` - 修复列表
- `/api/v1/repairs/execute` - 执行修复

### 系统管理端点
- `/api/v1/auth/login` - 用户认证
- `/api/v1/system/resources` - 系统资源
- `/api/v1/audit/logs` - 审计日志
- `/api/v1/enterprise/settings` - 企业设置

### 监控和追踪端点
- `/api/v1/apm/metrics` - APM指标
- `/api/v1/apm/traces` - APM追踪
- `/api/v1/tracing/data` - 追踪数据
- `/api/v1/monitoring/status` - 监控状态

### 基础设施端点
- `/api/v1/infrastructure/status` - 基础设施状态
- `/api/v1/k8s/pods` - Kubernetes Pod
- `/api/v1/docker/containers` - Docker容器
- `/api/v1/cloud/resources` - 云端资源

### 其他业务端点
- 工作流、插件、通知、成本分析、文档生成等

**总计**: 65+ API端点

## 测试场景

### 1. 阶梯式负载测试 (staircase)
逐步增加用户数，测试系统在不同负载下的性能表现。

**特点**:
- 从10用户开始，逐步增加到10000用户
- 每个阶梯持续60秒
- 适合确定系统性能拐点

### 2. 尖峰式负载测试 (spike)
模拟突发流量，测试系统的抗压能力。

**特点**:
- 基线100用户，尖峰10000用户
- 尖峰持续60秒
- 测试系统弹性

### 3. 波动式负载测试 (wave)
模拟真实场景中的流量波动。

**特点**:
- 使用正弦函数模拟流量波动
- 100-5000用户之间波动
- 波动周期2分钟

### 4. 恒定负载测试 (constant)
保持恒定的用户数，测试系统稳定性。

**特点**:
- 固定1000用户
- 持续运行指定时长
- 测试系统长期稳定性

### 5. 自定义负载测试 (custom)
自定义的负载测试场景，包含多个阶段。

**特点**:
- 多阶段负载变化
- 最高50000用户
- 完整的性能测试流程

## 并发级别

| 级别 | 用户数 | 生成速率 | 描述 |
|------|--------|----------|------|
| low | 10 | 5 | 低并发 - 模拟少量用户访问 |
| medium | 100 | 20 | 中并发 - 模拟中等用户访问 |
| high | 1000 | 100 | 高并发 - 模拟高用户访问 |
| very_high | 10000 | 1000 | 超高并发 - 模拟超高用户访问 |
| extreme | 50000 | 5000 | 极限并发 - 模拟极限用户访问 |

## 性能指标

测试自动收集以下性能指标：

- **响应时间**: P50, P95, P99
- **吞吐量**: RPS (Requests Per Second)
- **错误率**: 失败请求占比
- **资源利用率**: CPU, 内存使用率
- **并发数**: 当前并发用户数
- **请求分布**: 请求类型分布

## 使用方法

### 命令行运行

```bash
# 进入性能测试目录
cd tests/performance

# 运行阶梯式负载测试
python run_performance_test.py --scenario staircase

# 运行尖峰式负载测试
python run_performance_test.py --scenario spike

# 运行恒定负载测试（自定义参数）
python run_performance_test.py --scenario constant --users 1000 --duration 300

# 运行自定义负载测试
python run_performance_test.py --scenario custom

# 仅生成报告（从已有测试结果）
python run_performance_test.py --generate-reports-only
```

### 直接使用Locust

```bash
# 基本运行
locust -f locustfile.py --host http://localhost:8000

# 无头模式运行
locust -f locustfile.py --headless --users 1000 --spawn-rate 100 --run-time 300 --host http://localhost:8000

# 使用负载形状
locust -f locustfile.py --headless --shape locust_config.py::StaircaseLoadShape --host http://localhost:8000

# 生成HTML报告
locust -f locustfile.py --headless --users 1000 --spawn-rate 100 --run-time 300 --host http://localhost:8000 --html report.html
```

### 分布式测试

```bash
# 启动Master节点
locust -f locustfile.py --master --host http://localhost:8000

# 启动Worker节点（可多个）
locust -f locustfile.py --worker --master-host <master-ip>
```

## CI/CD集成

性能测试已集成到GitHub Actions，配置文件：`.github/workflows/performance-test.yml`

### 触发条件

- **Push事件**: main和develop分支
- **Pull Request**: 自动运行快速测试
- **定时任务**: 每天凌晨2点运行完整测试
- **手动触发**: 支持自定义参数

### 性能回归检测

- 自动检测性能回归（超过10%偏差）
- 严重回归（超过30%偏差）会导致测试失败
- 在PR中自动评论性能测试结果

## 报告生成

### HTML报告

生成的HTML报告包含：
- 测试摘要（总请求数、成功率等）
- 各API端点性能指标详情
- 性能基准对比
- 优化建议

### JSON报告

生成的JSON报告包含：
- 元数据（测试时间、环境等）
- 摘要统计
- 详细性能指标
- 可用于自动化分析

### 性能回归检测

自动检测性能回归：
- 加载性能基准（`docs/performance_baseline.md`）
- 对比当前性能与基准
- 生成告警信息

## 性能基准

性能基准定义在 `docs/performance_baseline.md`，包含各API端点的目标性能指标。

示例：
- `/health`: P95 < 20ms
- `/api/v1/alerts`: P95 < 100ms
- `/api/v1/ai/inference`: P95 < 2000ms

## 最佳实践

### 测试前准备

1. 确保应用已启动并可访问
2. 准备测试数据（如需要）
3. 确认测试环境配置正确
4. 关闭不必要的监控（避免干扰）

### 测试执行

1. 从小负载开始，逐步增加
2. 监控系统资源使用情况
3. 观察错误日志和异常
4. 记录测试环境配置

### 测试后分析

1. 查看性能报告
2. 分析性能瓶颈
3. 对比历史数据
4. 制定优化计划

## 故障排查

### 常见问题

**问题**: 连接被拒绝
- **解决**: 确认应用已启动，检查host配置

**问题**: 内存不足
- **解决**: 减少并发用户数，增加测试机器内存

**问题**: 测试超时
- **解决**: 增加超时时间，检查网络连接

**问题**: 性能回归误报
- **解决**: 检查基准数据是否准确，调整回归阈值

## 依赖项

```txt
locust>=2.15.0
pytest>=7.0.0
pytest-benchmark>=4.0.0
requests>=2.28.0
```

## 扩展开发

### 添加新的API端点测试

在 `locustfile.py` 中添加新的测试方法：

```python
@task(1)
def new_api_endpoint(self):
    """新API端点测试"""
    with self.client.get("/api/v1/new-endpoint", catch_response=True,
                        name="/api/v1/new-endpoint") as response:
        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Request failed: {response.status_code}")
```

### 添加新的负载形状

在 `locust_config.py` 中添加新的LoadTestShape类：

```python
class NewLoadShape(LoadTestShape):
    def tick(self):
        # 实现自定义负载逻辑
        return (users, spawn_rate)
```

## 贡献指南

1. 遵循项目代码规范
2. 添加适当的测试用例
3. 更新相关文档
4. 提交Pull Request

## 联系方式

- **性能测试团队**: performance-team@example.com
- **技术支持**: support@example.com

## 许可证

MIT License
