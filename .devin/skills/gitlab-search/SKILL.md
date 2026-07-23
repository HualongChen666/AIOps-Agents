---
name: gitlab-search
description: GitLab 代码搜索和 Issues 搜索功能
argument-hint: "[search_query]"
allowed-tools:
  - read_file
  - grep_search
  - find_by_name
  - bash
  - command_status
  - search_web
  - read_url_content
  - list_resources
  - read_resource
triggers:
  - user
  - model
subagent: false
priority: high
auto-apply:
  - "搜索代码"
  - "查找函数"
  - "搜索 Issues"
  - "GitLab 搜索"
  - "查找文件"
  - "代码搜索"
  - "查找实现"
keywords:
  - "搜索"
  - "查找"
  - "search"
  - "find"
  - "locate"
  - "GitLab"
  - "代码"
  - "函数"
  - "文件"
---

# GitLab Search Skill

## Purpose
优先使用 Devin 的 GitLab MCP 工具；若当前 agent session 未暴露 `mcp_call_tool`，
则使用 `bash` 调用 `.devin/scripts/gitlab_search.py` 作为后备方案。

## GitLab API 搜索功能

### 代码搜索
在 GitLab 仓库中搜索代码片段、函数、类等。

### Issues 搜索
搜索项目中的 Issues 和 Merge Requests。

### 文件搜索
查找仓库中的特定文件和目录。

### 项目搜索
搜索 GitLab 项目和群组。

## 搜索策略

### 1. 代码搜索模式
当用户要求搜索代码时：
- 使用 `bash` 执行：
  ```bash
  python .devin/scripts/gitlab_search.py search "<关键词>" --scope blobs --limit 10
  ```
- 如已限定项目，追加 `--project "Hualong_Chen/neurosync-agent-tool-platform"`。
- 支持 GitLab 高级搜索语法（如 `filename:main.py def aiops`）。

### 2. Issues 搜索模式
当用户要求查找相关 Issues 时：
- 使用 `bash` 执行：
  ```bash
  python .devin/scripts/gitlab_search.py search "<关键词>" --scope issues --limit 10
  ```
- 可追加 `--project "Hualong_Chen/neurosync-agent-tool-platform"` 限定项目。

### 3. 文件搜索模式
当用户要求查找特定文件时：
- 项目搜索：`python .devin/scripts/gitlab_search.py search "<关键词>" --scope projects`
- 读取文件内容：
  ```bash
  python .devin/scripts/gitlab_search.py file "<project_path>" "<file_path>" --ref main
  ```
- 示例：
  ```bash
  python .devin/scripts/gitlab_search.py file "bartkm/aiops-kafka-metrics-poc" README.md --ref main
  ```

### 4. 组合搜索模式
对于复杂的搜索需求：
- 结合代码搜索和 Issues 搜索
- 跨多个仓库搜索
- 使用 GitLab 的高级搜索语法

## GitLab 搜索语法

### 代码搜索语法
```gitlab
# 基本搜索
filename:main.py
def my_function

# 扩展搜索
filename:*.py def my_function
extension:py class User

# 按项目搜索
project:neurosync-agent-tool-platform def my_function
```

### Issues 搜索语法
```gitlab
# 基本 Issues 搜索
label::bug
state::opened
author::username

# 组合搜索
label::bug state::opened
milestone::v1.0
assignee::username
```

## 搜索工作流

### 代码搜索工作流
1. 理解用户的搜索需求
2. 构建适当的 GitLab 搜索查询
3. 调用 `python .devin/scripts/gitlab_search.py` 执行搜索
4. 分析搜索结果
5. 提供相关的代码片段和文件位置
6. 如果需要，使用 read 工具查看完整代码

### Issues 搜索工作流
1. 理解用户要查找的 Issue 类型
2. 构建 GitLab Issues 搜索查询
3. 调用 `python .devin/scripts/gitlab_search.py` 执行搜索
4. 分析相关的 Issues 和 MRs
5. 提供 Issue 链接和摘要
6. 如果需要，查看 Issue 详细内容

### 综合搜索工作流
1. 同时搜索代码和 Issues
2. 关联代码变更和相关的 Issues
3. 提供完整的上下文信息
4. 建议相关的文件和资源

## 搜索优化策略

### 搜索查询优化
- 使用具体的关键词而非通用术语
- 利用文件扩展名过滤
- 使用项目路径限定搜索范围
- 结合多个搜索条件

### 结果分析优化
- 优先显示最相关的结果
- 按时间和相关性排序
- 提供代码上下文
- 关联相关的 Issues 和 MRs

### 性能优化
- 限制搜索结果数量
- 使用缓存机制
- 避免过于宽泛的搜索
- 分批处理大型搜索请求

## 常见搜索场景

### 查找函数实现
```
用户: "找到 user authentication 函数的实现"
操作: 
- 搜索 "def authenticate" 或 "def login"
- 限制在 .py 文件中
- 查看相关文件
- 提供函数签名和实现位置
```

### 查找相关 Issues
```
用户: "查找与数据库连接相关的 Issues"
操作:
- 搜索带有 "database" 标签的 Issues
- 查找相关的 Merge Requests
- 提供 Issue 链接和状态
- 关联相关的代码变更
```

### 查找配置文件
```
用户: "找到数据库配置文件"
操作:
- 搜索包含 "database" 的配置文件
- 查找 config.py, .env 等文件
- 提供文件路径和内容摘要
```

### 查找 API 端点
```
用户: "找到用户相关的 API 端点"
操作:
- 搜索包含 "user" 的路由文件
- 查找 api/ 目录下的文件
- 提供 FastAPI 路由定义
- 关联相关的测试文件
```

## GitLab 搜索调用方式

### 项目搜索（默认）
```bash
python .devin/scripts/gitlab_search.py search "aiops" --scope projects --limit 10
```

### 代码搜索
```bash
python .devin/scripts/gitlab_search.py search "def my_function" --scope blobs --limit 10
```

限定项目：
```bash
python .devin/scripts/gitlab_search.py search "def my_function" --scope blobs --project "Hualong_Chen/neurosync-agent-tool-platform" --limit 10
```

### Issues 搜索
```bash
python .devin/scripts/gitlab_search.py search "label::bug state::opened" --scope issues --limit 10
```

### 读取文件内容
```bash
python .devin/scripts/gitlab_search.py file "Hualong_Chen/neurosync-agent-tool-platform" "main.py" --ref main
```

## GitLab 上传权限控制

### 严格上传控制规则
- **项目目录**: `C:\AIOps_Agent_bak`
- **上传权限**: 严格控制，只有得到用户明确指令才能上传
- **允许的上传指令格式**: "将某一个目录(含目录中的子目录和文件)或者某一个/几个文件(具体文件名)上传到我的gitlab中"
- **默认行为**: 没有明确上传指令时，禁止任何上传操作

### 上传操作检查清单
在执行任何GitLab上传操作前，必须：

1. **验证用户指令**: 检查用户是否给出了明确的上传指令
2. **检查指令格式**: 确认指令符合指定的格式要求
3. **确认上传内容**: 验证要上传的目录或文件是否在指令中明确指定
4. **获取用户确认**: 在上传前再次获得用户的明确确认
5. **记录操作日志**: 记录所有上传操作的详细信息

### 禁止的上传操作
- ❌ 未经用户明确指令的任何上传操作
- ❌ 自动上传代码到GitLab
- ❌ 批量上传未经验证的文件
- ❌ 上传敏感配置文件 (.env, .key等)
- ❌ 绕过上传控制机制

### 允许的GitLab操作
- ✅ 读取操作 (代码搜索、Issues查看)
- ✅ 搜索操作 (代码搜索、Issues搜索)
- ✅ 克隆操作 (从GitLab获取代码)
- ✅ 查看操作 (查看文件、提交历史)
- ⚠️ 上传操作 (仅在有明确上传指令时)

### 上传指令验证示例
```python
def validate_upload_command(user_command):
    """验证上传指令是否符合要求"""
    allowed_pattern = r"将.*上传到我的gitlab中"
    
    if not re.match(allowed_pattern, user_command):
        return False, "指令格式不符合要求"
    
    # 提取要上传的目录或文件
    # 验证路径是否在项目目录内
    # 确认用户明确指定了上传内容
    
    return True, "指令验证通过"
```

## 项目特定搜索

### 项目信息
- **项目路径**: `Hualong_Chen/neurosync-agent-tool-platform`
- **GitLab 实例**: `https://gitlab.dell.com`
- **主要代码目录**: `api/`, `core/`, `tests/`

### 常用搜索模式
```gitlab
# FastAPI 路由搜索
filename:api/*.py @router

# 数据库模型搜索
filename:core/*.py class.*Model

# 测试文件搜索
filename:tests/*.py def test_

# 配置文件搜索
filename:config*.py
```

## 搜索结果处理

### 结果格式化
- 提供清晰的文件路径
- 显示相关的代码片段
- 包含行号信息
- 提供 GitLab 链接

### 上下文提供
- 显示函数/类的完整签名
- 提供相关的文档字符串
- 关联相关的测试文件
- 链接到相关的 Issues

### 结果验证
- 确认搜索结果的准确性
- 验证代码的当前状态
- 检查是否有相关的更新
- 确认文件的可访问性

## 与其他工具的集成

### 与本地搜索结合
- 先使用 GitLab 搜索查找相关文件
- 然后使用本地 grep 工具进行详细搜索
- 结合 read 工具查看完整内容

### 与 Skills 协作
- 与 python-development skill 结合分析代码质量
- 与 fastapi-development skill 结合分析 API 结构
- 与 testing-debugging skill 结合查找相关测试

## 搜索最佳实践

1. **具体化搜索**: 使用具体的关键词和文件类型
2. **分步搜索**: 从宽泛搜索逐步缩小范围
3. **验证结果**: 确认搜索结果的准确性和相关性
4. **提供上下文**: 不仅提供搜索结果，还要提供相关上下文
5. **持续优化**: 根据搜索结果优化搜索策略

## 错误处理

### 搜索失败处理
- 检查 GitLab 连接状态
- 验证搜索查询语法
- 提供替代搜索方案
- 使用本地搜索作为后备

### 无结果处理
- 优化搜索查询
- 扩大搜索范围
- 提供搜索建议
- 尝试不同的搜索策略

## 性能考虑

- 避免过于复杂的搜索查询
- 限制搜索结果数量
- 使用缓存机制
- 分批处理大型搜索请求

## When to Invoke
当用户需要以下功能时自动触发此 skill：
- 搜索代码实现
- 查找相关 Issues
- 搜索特定文件
- 查找 API 端点
- 查找配置信息
- 任何与项目资源相关的搜索需求

## Project Context
此 skill 针对 AIOps Agent 项目：
- GitLab 项目: `Hualong_Chen/neurosync-agent-tool-platform`
- GitLab 实例: `https://gitlab.dell.com`
- 主要搜索范围: Python 代码、FastAPI 路由、数据库模型、测试文件