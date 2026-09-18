# CodingSubAgent增强功能API文档

## 概述

CodingSubAgent增强功能为原有的110行代码添加了超时机制、参数验证、并发控制、线程安全、进度显示、性能监控、安全加固等功能。

## 环境变量配置

### 超时配置
- `SUBAGENT_TIMEOUT_SECONDS`: 工具执行超时时间（秒），默认60
- `SUBAGENT_STALL_TIMEOUT_SECONDS`: 停滞检测超时时间（秒），默认120
- `API_TIMEOUT_MS`: API调用超时时间（毫秒），默认120000

### 并发配置
- `MAX_CONCURRENT_SUBAGENTS`: 最大并发子agent数，默认5
- `MAX_CONCURRENT_TOOL_EXECUTIONS`: 最大并发工具执行数，默认10

### 功能开关
- `ENABLE_TIMEOUT`: 启用超时机制，默认true
- `ENABLE_VALIDATION`: 启用参数验证，默认true
- `ENABLE_WHITELIST`: 启用工具白名单，默认true
- `ENABLE_PROGRESS`: 启用进度显示，默认false
- `ENABLE_STALL_DETECTION`: 启用停滞检测，默认false

### 工具白名单
- `ALLOWED_TOOLS`: 允许的工具列表，默认"bash,read_file,write_to_file,edit"

## API使用

### 基本使用（向后兼容）

```python
from core.agent.coding_subagent import CodingSubAgent

agent = CodingSubAgent(agent_id="test_agent")
result = agent.run(
    goal="执行bash命令",
    context={"tool": "bash", "params": {"command": "ls"}},
    available_tools=["bash", "read_file"]
)
```

### 增强功能使用

```python
from core.agent.coding_subagent import CodingSubAgent

agent = CodingSubAgent(agent_id="test_agent")

# 增强功能自动启用
result = agent.run(
    goal="执行bash命令",
    context={"tool": "bash", "params": {"command": "ls"}, "timeout": 30},
    available_tools=["bash", "read_file"]
)

# 获取性能指标
if agent._enhanced_enabled:
    performance = agent.performance.get_summary()
    print(f"平均执行时间: {performance['avg_time']}秒")
    print(f"错误率: {performance['error_rate']:.2%}")

# 获取安全审计报告
if agent._enhanced_enabled:
    audit_report = agent.security.get_audit_report()
    print(f"总执行次数: {audit_report['total_executions']}")
    print(f"成功率: {audit_report['success_rate']:.2%}")
```

## 降级策略

系统提供二级降级策略：
- **full级别**: 启用所有功能（超时、验证、白名单）
- **minimal级别**: 只启用超时功能

当系统健康状态不佳时，自动降级到minimal级别。

## 安全特性

1. **参数验证**: 验证必需字段、字段类型、工具白名单
2. **命令注入检测**: 检测bash命令中的危险字符
3. **路径穿越检测**: 检测文件路径中的路径穿越
4. **审计日志**: 记录所有工具执行，清理敏感信息
5. **可疑活动检测**: 检测高失败率的工具

## 性能特性

1. **超时控制**: 防止工具执行无限等待
2. **停滞检测**: 检测工具执行停滞
3. **并发控制**: 使用Semaphore限制并发数
4. **性能监控**: 记录执行时间、错误率、超时率
5. **线程安全**: 主线程初始化，工作线程执行

## 向后兼容性

所有增强功能通过功能开关控制，默认启用但可通过环境变量禁用。如果增强功能组件不可用，系统自动降级到原始实现。