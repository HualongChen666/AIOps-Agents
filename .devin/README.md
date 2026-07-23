# Devin IDE 配置说明

为 AIOps Agent 项目配置的 Python 开发工具和技能。

## 🚀 已配置的工具和技能

### MCP 服务器

1. **GitLab MCP** - GitLab 集成和搜索
   - 代码仓库操作
   - MR 管理
   - Issue 跟踪
   - **代码搜索功能** - 主要搜索解决方案
   - Issues 搜索和查询
   - 需要配置: `GITLAB_PERSONAL_ACCESS_TOKEN`, `GITLAB_API_URL`（建议仅写入 `.devin/config.local.json`，不要提交到仓库）

2. **Filesystem MCP** - 增强文件操作
   - 高级文件搜索
   - 批量文件操作
   - 路径: `C:\AIOps_Agent_bak`

3. **Postgres MCP** - PostgreSQL 数据库操作
   - 直接数据库查询
   - Schema 管理
   - 需要配置: `POSTGRES_CONNECTION_STRING`

### 自定义 Skills

1. **auto-task-execute** - 全自动任务执行
   - 读取 `task_list.md`
   - 规划、合并、并行执行任务
   - 自动验收与质量检查

2. **auto-task-verify** - 全自动任务核验
   - 对 `task_list.md` 指定范围任务执行十维度核验
   - 生成核验报告

3. **gitlab-search** - GitLab 搜索功能
   - 代码搜索和查询
   - Issues 和 MR 搜索
   - 项目资源查找
   - 主要搜索解决方案

4. **python-development** - Python 开发最佳实践
   - 自动代码质量检查
   - 项目特定约定
   - 安全最佳实践

5. **fastapi-development** - FastAPI 开发模式
   - API 设计原则
   - 异步数据库操作
   - 错误处理模式

6. **testing-debugging** - 测试和调试
   - Pytest 配置
   - 调试策略
   - 性能测试

7. **database-migration** - 数据库迁移
   - Alembic 使用
   - 迁移模式
   - 数据迁移

8. **grill-me** - 追问式设计评审
   - 逐层展开决策树
   - 每次只问一个问题
   - 不产出文件，直到达成共同理解

9. **tdd** - 测试驱动开发
   - red-green-refactor 循环
   - 每次只切一个垂直切片
   - 只测试公共接口行为

10. **grill-with-docs** - 边追问边建模

- 实时维护 `CONTEXT.md` 词汇表
- 记录关键架构决策 ADR
- 在 `docs/adr/` 中生成文档

## 🔧 配置步骤

### 1. 配置敏感信息

编辑 `.devin/config.local.json` 文件，填入你的 API 密钥：

```json
{
  "mcpServers": {
    "gitlab": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-gitlab"],
      "env": {
        "GITLAB_PERSONAL_ACCESS_TOKEN": "你的GitLab令牌",
        "GITLAB_API_URL": "你的GitLab实例URL"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://用户:密码@localhost:5432/数据库名"
      }
    }
  }
}
```

### 2. 获取 API 密钥

**GitLab Token:**

- 访问你的 GitLab 实例 (如 <https://gitlab.com>)
- 进入 User Settings -> Access Tokens
- 生成新的 Personal Access Token
- 选择需要的权限 (api, read_repository, write_repository 等)
- 对于自托管的 GitLab，使用你的 GitLab URL

**PostgreSQL Connection String:**

- 格式: `postgresql://用户名:密码@主机:端口/数据库名`
- 示例: `postgresql://postgres:password@localhost:5432/aiops`

### 3. 验证配置

验证 MCP 服务器配置：

1. 打开 Devin Desktop，在 MCP 面板中确认各服务器状态。
2. 在终端中可用新的 CLI 名称 `devin-desktop` 启动 Devin：

```bash
# 检查 Devin Desktop 版本
devin-desktop --version
```

> 注意：Devin Desktop 升级后，`devin` 命令已更名为 `devin-desktop`。

## 🎯 使用技能

### 自动触发

这些技能会在以下情况自动触发：

- **python-development**: 编辑 .py 文件时
- **fastapi-development**: 创建 API 路由时
- **testing-debugging**: 编写或运行测试时
- **database-migration**: 修改数据库 schema 时
- **grill-me**: 用户提到 "grill me"、"压力测试设计"、"挑战我的方案"、"帮我把方案想清楚" 等
- **tdd**: 用户提到 "tdd"、"测试驱动开发"、"先写测试"、"red-green-refactor" 等
- **grill-with-docs**: 用户提到 "grill with docs"、"边问边写文档"、"创建 CONTEXT.md"、"记录架构决策" 等

### 手动调用

你也可以手动调用技能：

```
/auto-task-execute [任务范围，例如 任务1~任务5]
/auto-task-verify [任务范围，例如 任务1~任务5]
/gitlab-search [搜索查询]
/python-development [任务描述]
/fastapi-development [端点描述]
/testing-debugging [测试文件]
/database-migration [迁移描述]
/grill-me [主题或方案]
/tdd [功能或 bug 描述]
/grill-with-docs [计划或设计]
```

### 搜索功能

**GitLab 搜索** (主要搜索解决方案)：

- 代码搜索：`/gitlab-search "def my_function"`
- Issues 搜索：`/gitlab-search "label::bug"`
- 文件搜索：`/gitlab-search "filename:config.py"`
- 组合搜索：`/gitlab-search "api router user"`

**本地搜索** (补充搜索)：

- 使用 `grep_search` 进行本地代码搜索
- 使用 `find_by_name` 进行文件查找

## 📋 自动质量检查

配置的技能会自动执行以下质量检查：

1. **类型检查**: `python -m mypy .`
2. **代码格式化**: `python -m black --check .`
3. **Linting**: `python -m flake8 .`
4. **安全检查**: `bandit -r .`
5. **导入排序**: `python -m isort --check-only .`
6. **测试覆盖率**: `pytest --cov=. --cov-report=html`

## 🛠️ 开发工作流

### 典型开发流程

1. **创建新功能**
   - 使用 `/fastapi-development` 创建 API 端点
   - 技能会自动应用项目约定和最佳实践

2. **编写代码**
   - `/python-development` 会自动应用代码质量标准
   - 自动检查类型提示和文档字符串

3. **数据库变更**
   - 使用 `/database-migration` 创建 Alembic 迁移
   - 自动生成升级和降级脚本

4. **测试**
   - 使用 `/testing-debugging` 编写测试
   - 自动运行覆盖率检查

5. **调试**
   - 技能会提供调试策略和工具
   - 自动日志分析和错误追踪

## 🔍 MCP 权限配置

已配置的权限：

- **允许**: GitLab 操作（包括搜索）、文件系统操作、Postgres 查询
- **询问**: Postgres 写操作 (需要确认)

可以在 `.devin/config.json` 中调整权限设置。

## 🔎 GitLab 搜索功能详解

### 搜索能力

GitLab MCP 提供强大的搜索功能，作为项目的主要搜索解决方案：

1. **代码搜索**
   - 搜索函数、类、变量
   - 按文件类型过滤
   - 支持正则表达式
   - 跨仓库搜索

2. **Issues 搜索**
   - 按标签、状态、作者搜索
   - 查找相关的 Merge Requests
   - 搜索项目讨论
   - 跟踪问题进展

3. **文件搜索**
   - 按文件名和路径搜索
   - 查找配置文件
   - 定位资源文件
   - 搜索特定目录

### 搜索示例

```bash
# 搜索函数实现
/gitlab-search "def authenticate_user"

# 搜索 FastAPI 路由
/gitlab-search "@router.post"

# 查找相关 Issues
/gitlab-search "label::bug database"

# 搜索配置文件
/gitlab-search "filename:config.py"

# 组合搜索
/gitlab-search "filename:api/*.py @router"
```

### 搜索优势

- **项目集成**: 直接搜索 GitLab 仓库，无需本地索引
- **实时更新**: 始终搜索最新代码
- **历史版本**: 可以搜索历史提交
- **团队协作**: 可以搜索团队成员的代码和 Issues
- **跨仓库**: 支持在多个项目中搜索

## 📈 预期效果

配置这些工具和技能后，Devin IDE 将会：

1. **更智能**: 自动应用项目特定的最佳实践
2. **更高效**: 减少手动配置和重复工作
3. **更高质量**: 自动执行代码质量检查
4. **更快捷**: 智能工具选择和调用
5. **更安全**: 自动安全检查和敏感信息保护
6. **强大搜索**: GitLab 集成搜索，覆盖代码、Issues、MRs

## 🆘 故障排除

### MCP 服务器无法连接

1. 检查 API 密钥是否正确
2. 验证网络连接
3. 查看 Devin IDE 日志

### 技能未触发

1. 确认技能文件存在且格式正确
2. 检查 frontmatter 配置
3. 重启 Devin IDE

### 权限问题

1. 检查 `.devin/config.json` 中的权限设置
2. 确认 MCP 服务器配置正确
3. 查看权限错误日志

## 📚 相关文档

- [Devin CLI 文档](https://cli.devin.ai/docs)
- [MCP 配置指南](https://cli.devin.ai/docs/extensibility/mcp)
- [Skills 创建指南](https://cli.devin.ai/docs/extensibility/skills)
- [项目 AGENTS.md](./AGENTS.md) (如果存在)

## 🔄 更新配置

要更新配置：

1. 编辑 `.devin/config.json` 或 `.devin/config.local.json`
2. 重启 Devin IDE
3. 打开 Devin Desktop 的 MCP 面板，确认服务器已连接

配置文件说明：

- `config.json`: 项目共享配置 (可提交到 Git)
- `config.local.json`: 本地配置 (不提交，包含敏感信息)
