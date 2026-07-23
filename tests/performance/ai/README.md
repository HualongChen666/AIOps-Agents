# AI Performance Tests

## 概述

本目录包含AIOps Agent的AI推理性能测试框架，基于pytest-benchmark实现，支持LLM推理、RAG系统、向量检索、代理编排等AI核心功能的性能测试。

## 目录结构

```
tests/performance/ai/
├── __init__.py                      # 包初始化文件
├── test_llm_performance.py          # LLM推理性能测试
├── test_rag_performance.py          # RAG系统性能测试
├── test_agent_performance.py        # 代理编排性能测试
├── ai_cost_monitor.py              # AI成本监控工具
├── ai_report_generator.py          # AI性能报告生成器
├── run_ai_performance_test.py      # 命令行运行脚本
└── README.md                        # 本文档
```

## 测试覆盖场景

### 1. LLM推理性能测试 (test_llm_performance.py)

**基础推理测试**:
- 短提示词推理性能
- 中等长度提示词推理性能
- 长提示词推理性能

**模型对比测试**:
- 不同模型推理性能对比（gpt-3.5-turbo, gpt-4, claude-3-sonnet, claude-3-opus）
- temperature参数影响
- max_tokens参数影响

**高级功能测试**:
- 流式推理性能
- 批量推理性能
- 并发推理性能
- 失败重试性能

**质量指标测试**:
- 响应时间P50/P95/P99
- 错误率测试

**成本监控测试**:
- Token消耗统计
- 不同模型成本对比
- 成本优化建议

### 2. RAG系统性能测试 (test_rag_performance.py)

**端到端性能测试**:
- RAG端到端延迟测试（目标：< 5秒）
- 检索性能测试
- 生成性能测试

**配置优化测试**:
- 不同top_k值的性能对比
- 不同查询复杂度的性能对比
- RAG缓存性能测试
- 并发RAG查询性能

**向量检索测试**:
- 1000维向量检索性能（目标：< 100ms）
- 批量向量检索性能
- 不同集合大小的向量检索性能
- 向量索引性能测试
- 相似度阈值对性能的影响

**质量指标测试**:
- 检索精确度
- 检索召回率
- 响应相关性
- RAG F1分数

### 3. 代理编排性能测试 (test_agent_performance.py)

**代理执行测试**:
- 单代理执行性能
- 顺序代理执行性能
- 并行代理执行性能

**代理协作测试**:
- 代理间通信性能
- 代理协调性能
- 复杂代理工作流性能
- 代理错误处理性能
- 代理状态管理性能
- 代理可扩展性测试

**LangGraph测试**:
- 简单图执行性能
- 分支图执行性能
- 循环图执行性能
- 条件图执行性能
- 图状态持久化性能

**多代理协作测试**:
- 多代理协作性能
- 代理协商性能

### 4. AI成本监控 (ai_cost_monitor.py)

**成本追踪功能**:
- 模型定价管理
- Token使用记录
- 成本计算
- 按模型成本统计
- 按模型使用统计
- 成本趋势分析

**优化建议**:
- 模型降级建议
- Token优化建议
- 缓存建议
- 批量处理建议

## 使用方法

### 运行所有AI性能测试

```bash
# 进入项目根目录
cd C:\AIOps_Agent_bak

# 运行所有AI性能测试
pytest tests/performance/ai/ -v --benchmark-only

# 生成HTML报告
pytest tests/performance/ai/ -v --benchmark-only --benchmark-html=reports/ai_benchmark.html
```

### 运行特定测试文件

```bash
# 运行LLM性能测试
pytest tests/performance/ai/test_llm_performance.py -v --benchmark-only

# 运行RAG性能测试
pytest tests/performance/ai/test_rag_performance.py -v --benchmark-only

# 运行代理性能测试
pytest tests/performance/ai/test_agent_performance.py -v --benchmark-only
```

### 运行特定测试用例

```bash
# 运行单个测试
pytest tests/performance/ai/test_llm_performance.py::TestLLMPerformance::test_llm_inference_short_prompt -v --benchmark-only

# 运行特定测试类
pytest tests/performance/ai/test_llm_performance.py::TestLLMPerformance -v --benchmark-only
```

### 使用AI成本监控

```python
# 在Python脚本中使用
from tests.performance.ai.ai_cost_monitor import AICostMonitor, monitor_ai_costs

# 创建监控器
monitor = AICostMonitor()

# 记录使用情况
monitor.record_usage("gpt-3.5-turbo", prompt_tokens=100, completion_tokens=200)

# 生成报告
report = monitor.generate_cost_report()
print(report)

# 获取优化建议
suggestions = monitor.generate_optimization_suggestions()
for suggestion in suggestions:
    print(f"[{suggestion['priority']}] {suggestion['suggestion']}")

# 使用便捷函数
cost_info = await monitor_ai_costs("gpt-3.5-turbo", 100, 200)
print(cost_info)
```

### 使用命令行运行脚本

```bash
# 运行所有AI性能测试
python tests/performance/ai/run_ai_performance_test.py --all

# 运行特定测试类型
python tests/performance/ai/run_ai_performance_test.py --llm
python tests/performance/ai/run_ai_performance_test.py --rag
python tests/performance/ai/run_ai_performance_test.py --agent

# 生成成本报告
python tests/performance/ai/run_ai_performance_test.py --cost-report

# 生成性能报告
python tests/performance/ai/run_ai_performance_test.py --generate-report
```

## 性能基准

根据 `docs/performance_baseline.md`，AI性能基准如下：

### LLM推理基准

| 操作 | 模型 | 目标P95(ms) |
|------|------|-------------|
| 短提示词推理 | gpt-3.5-turbo | 500 |
| 中等提示词推理 | gpt-3.5-turbo | 1000 |
| 长提示词推理 | gpt-3.5-turbo | 2000 |
| 短提示词推理 | gpt-4 | 1500 |
| 流式推理 | gpt-3.5-turbo | 300 |

### RAG系统基准

| 操作 | 目标P95(ms) |
|------|-------------|
| 文档检索 | 100 |
| 答案生成 | 500 |
| 端到端延迟 | 5000 |

### 向量检索基准

| 操作 | 向量维度 | 目标P95(ms) |
|------|----------|-------------|
| 单次检索 | 1000 | 100 |
| 批量检索(10) | 1000 | 500 |
| 百万级集合检索 | 1000 | 200 |

### 代理编排基准

| 操作 | 代理数量 | 目标P95(ms) |
|------|----------|-------------|
| 单代理执行 | 1 | 200 |
| 并行代理执行 | 5 | 500 |
| 复杂工作流 | 3 | 1000 |

## 性能优化建议

### 1. LLM推理优化

- 选择合适的模型（根据任务复杂度）
- 优化提示词长度
- 使用流式推理改善用户体验
- 实现响应缓存减少重复推理
- 使用批量处理API降低成本

### 2. RAG系统优化

- 优化检索算法（提高精确度）
- 调整top_k参数（平衡性能和质量）
- 实现检索结果缓存
- 使用更快的向量数据库
- 优化文档分块策略

### 3. 向量检索优化

- 选择合适的向量维度
- 使用近似最近邻算法
- 优化索引结构
- 考虑使用GPU加速
- 实现批量检索

### 4. 代理编排优化

- 减少代理间通信开销
- 使用并行执行提高效率
- 优化状态管理
- 实现代理缓存
- 使用更高效的协调算法

### 5. 成本优化

- 根据任务选择合适的模型
- 优化Token使用
- 实现响应缓存
- 使用批量处理
- 监控成本趋势

## 报告生成

### HTML报告

生成的HTML报告包含：
- 测试摘要（总测试数、通过/失败、总成本、总Token数）
- LLM推理性能详情
- RAG系统性能详情
- 向量检索性能详情
- 代理编排性能详情
- 成本分析
- 优化建议

### JSON报告

生成的JSON报告包含：
- 元数据（测试时间、环境）
- 摘要统计
- 详细性能指标
- 成本分析
- 优化建议

## CI/CD集成

AI性能测试可以集成到CI/CD流程中：

```yaml
# .github/workflows/ai-performance-test.yml
name: AI Performance Tests

on:
  push:
    branches: [ main, develop ]
  schedule:
    - cron: '0 4 * * *'  # 每天凌晨4点运行

jobs:
  ai-performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install pytest pytest-benchmark
      - name: Run AI performance tests
        run: |
          pytest tests/performance/ai/ -v --benchmark-only --benchmark-json=ai_benchmark.json
      - name: Upload benchmark results
        uses: actions/upload-artifact@v3
        with:
          name: ai-benchmark-results
          path: ai_benchmark.json
```

## 故障排查

### 常见问题

**问题**: API调用失败
- **解决**: 检查API密钥配置，确保网络连接正常

**问题**: 测试超时
- **解决**: 增加超时时间，检查网络延迟

**问题**: 成本计算不准确
- **解决**: 更新模型定价配置

**问题**: 向量检索性能差
- **解决**: 检查向量索引是否正确创建，考虑使用近似算法

## 依赖项

```txt
pytest>=7.0.0
pytest-benchmark>=4.0.0
```

## 扩展开发

### 添加新的AI性能测试

在相应的测试文件中添加新的测试方法：

```python
@pytest.mark.asyncio
async def test_new_ai_scenario(self, benchmark):
    """新的AI性能测试场景"""
    async def new_scenario():
        # 实现测试逻辑
        pass
    
    benchmark.pedantic(new_scenario)
```

### 添加新的模型定价

在 `ai_cost_monitor.py` 中添加新的模型定价：

```python
monitor = AICostMonitor()
monitor.add_pricing("new-model", input_price=0.001, output_price=0.002)
```

## 贡献指南

1. 遵循项目代码规范
2. 添加适当的测试用例
3. 更新相关文档
4. 提交Pull Request

## 联系方式

- **AI性能测试团队**: ai-perf-team@example.com
- **技术支持**: support@example.com

## 许可证

MIT License
