# CodingSubAgent增强功能配置指南

## 环境变量配置

### 开发环境配置

在`.env.development`中配置：

```bash
# 超时配置（较短，便于开发调试）
SUBAGENT_TIMEOUT_SECONDS=60
SUBAGENT_STALL_TIMEOUT_SECONDS=120

# 并发配置（较低，避免资源占用）
MAX_CONCURRENT_SUBAGENTS=5
MAX_CONCURRENT_TOOL_EXECUTIONS=10

# 功能开关（启用核心功能）
ENABLE_TIMEOUT=true
ENABLE_VALIDATION=true
ENABLE_WHITELIST=true
ENABLE_PROGRESS=false
ENABLE_STALL_DETECTION=false
```

### 预发布环境配置

在`.env.staging`中配置：

```bash
# 超时配置（适中）
SUBAGENT_TIMEOUT_SECONDS=60
SUBAGENT_STALL_TIMEOUT_SECONDS=120

# 并发配置（适中）
MAX_CONCURRENT_SUBAGENTS=5
MAX_CONCURRENT_TOOL_EXECUTIONS=10

# 功能开关（启用核心功能）
ENABLE_TIMEOUT=true
ENABLE_VALIDATION=true
ENABLE_WHITELIST=true
ENABLE_PROGRESS=false
ENABLE_STALL_DETECTION=false
```

### 生产环境配置

在`.env.production`中配置：

```bash
# 超时配置（保守）
SUBAGENT_TIMEOUT_SECONDS=60
SUBAGENT_STALL_TIMEOUT_SECONDS=120

# 并发配置（保守）
MAX_CONCURRENT_SUBAGENTS=5
MAX_CONCURRENT_TOOL_EXECUTIONS=10

# 功能开关（启用核心功能）
ENABLE_TIMEOUT=true
ENABLE_VALIDATION=true
ENABLE_WHITELIST=true
ENABLE_PROGRESS=false
ENABLE_STALL_DETECTION=false
```

## 工具白名单配置

### 默认白名单

默认允许的工具：`bash,read_file,write_to_file,edit`

### 自定义白名单

通过环境变量`ALLOWED_TOOLS`配置：

```bash
# 只允许读取文件
ALLOWED_TOOLS=read_file

# 允许所有操作
ALLOWED_TOOLS=bash,read_file,write_to_file,edit

# 禁止bash命令
ALLOWED_TOOLS=read_file,write_to_file,edit
```

## 功能开关配置

### 启用所有功能

```bash
ENABLE_TIMEOUT=true
ENABLE_VALIDATION=true
ENABLE_WHITELIST=true
ENABLE_PROGRESS=true
ENABLE_STALL_DETECTION=true
```

### 禁用所有增强功能

```bash
ENABLE_TIMEOUT=false
ENABLE_VALIDATION=false
ENABLE_WHITELIST=false
ENABLE_PROGRESS=false
ENABLE_STALL_DETECTION=false
```

### 只启用超时和验证

```bash
ENABLE_TIMEOUT=true
ENABLE_VALIDATION=true
ENABLE_WHITELIST=false
ENABLE_PROGRESS=false
ENABLE_STALL_DETECTION=false
```

## 性能调优

### 超时时间调优

- **开发环境**: 60秒（快速失败）
- **预发布环境**: 60秒（适中）
- **生产环境**: 60秒（保守）

### 并发数调优

- **开发环境**: 5个并发（避免资源占用）
- **预发布环境**: 5个并发（适中）
- **生产环境**: 5个并发（保守）

### 功能开关调优

- **核心功能**: 超时、验证、白名单（始终启用）
- **可选功能**: 进度显示、停滞检测（按需启用）

## 配置验证

启动时会自动验证配置参数的合理性：

- 超时时间范围：1-600秒
- 并发数范围：1-20
- 工具白名单：不能为空
- 功能开关：必须是true/false

如果配置无效，系统会记录警告并使用默认值。