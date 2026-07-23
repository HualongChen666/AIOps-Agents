---
name: project-conventions
description: AIOps Agent项目特定约定和规范
---

# AIOps Agent 项目约定

## 项目概览

### 项目信息
- **项目名称**: AIOps Agent
- **主要语言**: Python 3.10+
- **主要框架**: FastAPI
- **数据库**: PostgreSQL (异步)
- **缓存**: Redis
- **GitLab**: https://gitlab.dell.com/Hualong_Chen/neurosync-agent-tool-platform

### 技术栈
- FastAPI + Uvicorn
- SQLAlchemy 2.0 (异步)
- Pydantic v2
- Alembic (数据库迁移)
- Redis (缓存)
- OpenTelemetry (监控)
- Pytest (测试)

## 目录结构约定

### 核心目录
```
AIOps_Agent_bak/
├── api/                    # FastAPI路由 (70+ routers)
├── core/                   # 核心功能模块
│   ├── ai/                # AI/ML集成
│   ├── agent/             # Agent系统
│   └── database/          # 数据库配置
├── tests/                 # 测试套件
├── alembic/               # 数据库迁移
├── scripts/               # 工具脚本
└── main.py               # 应用入口
```

### 文件命名约定
- 路由文件: `{resource}_router.py`
- 模型文件: `{model}.py`
- 测试文件: `test_{module}.py`
- 配置文件: `config.py`

## 开发工作流约定

### 代码提交流程
1. 创建功能分支
2. 编写代码和测试
3. 运行质量检查
4. 提交到GitLab
5. 创建Merge Request
6. 代码审查
7. 合并到主分支

### 质量检查流程
```bash
# 1. 代码格式化
python -m black .

# 2. 类型检查
python -m mypy .

# 3. 代码质量检查
python -m flake8 .

# 4. 安全检查
bandit -r .

# 5. 测试运行
pytest --cov=. --cov-report=html
```

## GitLab工作流约定

### 项目目录
- **项目目录**: `C:\AIOps_Agent_bak`
- **GitLab项目**: `https://gitlab.dell.com/Hualong_Chen/neurosync-agent-tool-platform.git`
- **项目路径**: `Hualong_Chen/neurosync-agent-tool-platform`

### 分支策略
- `main`: 主分支，生产代码
- `develop`: 开发分支
- `feature/*`: 功能分支
- `bugfix/*`: 修复分支
- `hotfix/*`: 紧急修复

### Merge Request约定
- MR标题格式: `type: description`
- 类型: feature, bugfix, hotfix, docs, refactor
- 必须关联相关Issue
- 必须通过所有CI检查
- 至少一人审查批准

### Issue管理
- 使用标签分类: bug, feature, enhancement, documentation
- 设置优先级: critical, high, medium, low
- 指定负责人和里程碑
- 关联相关的Merge Requests

## GitLab上传控制规则

### 上传权限控制
- **严格上传控制**: 已启用
- **上传指令要求**: 必须使用明确的上传指令格式
- **允许的上传指令**: "将某一个目录(含目录中的子目录和文件)或者某一个/几个文件(具体文件名)上传到我的gitlab中"
- **默认行为**: 没有明确上传指令时，禁止任何上传操作

### 上传操作规范
1. **明确指令**: 只有在用户明确给出上传指令时才执行上传操作
2. **指令格式**: 必须符合指定的指令格式
3. **权限验证**: 每次上传操作前必须验证用户权限
4. **操作日志**: 所有GitLab操作必须记录日志
5. **用户确认**: 上传操作前必须获得用户明确确认

### 禁止的上传行为
- ❌ 未经用户明确指令的任何上传操作
- ❌ 自动上传代码到GitLab
- ❌ 批量上传未经验证的文件
- ❌ 上传敏感配置文件
- ❌ 绕过上传控制机制

### 允许的GitLab操作
- ✅ 读取操作 (代码搜索、Issues查看)
- ✅ 搜索操作 (代码搜索、Issues搜索)
- ✅ 克隆操作 (从GitLab获取代码)
- ✅ 查看操作 (查看文件、提交历史)
- ⚠️ 上传操作 (仅在有明确上传指令时)

## 环境配置约定

### 环境变量
```env
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/aiops
REDIS_URL=redis://localhost:6379

# AI服务
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# 应用配置
LOG_LEVEL=INFO
DEBUG=False
ENVIRONMENT=development
```

### 配置文件优先级
1. 环境变量
2. .env.local (本地开发，不提交)
3. .env (默认配置)
4. config.py (代码默认值)

## 监控和日志约定

### 日志规范
- 使用loguru日志库
- 日志级别: DEBUG, INFO, WARNING, ERROR
- 结构化日志格式
- 敏感信息脱敏

### 监控指标
- API响应时间
- 错误率
- 数据库连接数
- Redis连接数
- 内存使用情况

### 告警规则
- 错误率 > 5%
- 响应时间 > 1s
- 数据库连接数 > 80%
- 内存使用 > 90%

## 安全约定

### 认证授权
- JWT token认证
- 基于角色的访问控制 (RBAC)
- Token过期时间: 1小时
- 刷新token机制

### 数据保护
- 敏感数据加密存储
- 传输层加密 (TLS)
- 定期安全审计
- 依赖漏洞扫描

### API安全
- 速率限制
- 输入验证和过滤
- SQL注入防护
- XSS防护

## 性能约定

### 响应时间目标
- API响应: < 200ms
- 数据库查询: < 100ms
- 页面加载: < 2s

### 资源使用限制
- 内存: < 2GB per instance
- CPU: < 80% per instance
- 数据库连接: < 100 per instance

### 缓存策略
- Redis缓存热点数据
- 缓存过期时间: 5-30分钟
- 缓存命中率: > 80%

## 测试约定

### 测试类型
- 单元测试: 测试单个函数/类
- 集成测试: 测试模块间交互
- 端到端测试: 测试完整流程
- 性能测试: 负载和压力测试

### 测试覆盖率目标
- 整体覆盖率: > 80%
- 核心模块: > 90%
- API路由: > 85%

### 测试数据管理
- 使用测试数据库
- 数据工厂模式
- 测试数据清理
- 隔离测试环境

## 文档约定

### 代码文档
- 所有公开函数必须有docstring
- 使用Google风格docstring
- 复杂逻辑添加注释
- API文档使用OpenAPI

### 项目文档
- README.md: 项目概述和快速开始
- AGENTS.md: 开发约定和工作流
- API文档: 自动生成OpenAPI文档
- 变更日志: CHANGELOG.md

## 故障排除约定

### 常见问题处理
- 数据库连接失败
- Redis连接失败
- API响应超时
- 内存泄漏

### 调试流程
1. 查看应用日志
2. 检查系统资源
3. 验证配置正确性
4. 测试依赖服务
5. 分析性能指标

### 应急响应
- 服务降级策略
- 数据备份恢复
- 回滚机制
- 通知机制