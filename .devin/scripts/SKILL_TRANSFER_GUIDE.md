# 打包/迁移 `auto-task-execute` 与 `auto-task-verify` Skill 指南

## 1. 概述

本指南说明如何把 `.devin/skills/auto-task-execute/` 与 `.devin/skills/auto-task-verify/` 打包并迁移给别人使用，以及接收方需要做哪些本地化改造。

**核心文件**：
- `.devin/skills/auto-task-execute/SKILL.md`
- `.devin/skills/auto-task-verify/SKILL.md`

这两个 skill 是为 `C:\AIOps_Agent_bak` 项目量身定制的，直接转发后必须做本地化改造才能正常运行。

---

## 2. 需要一起转发的文件清单

### 2.1 必须转发的 Skill 文件

```
.devin/
├── skills/
│   ├── auto-task-execute/
│   │   └── SKILL.md
│   ├── auto-task-verify/
│   │   └── SKILL.md
│   ├── python-development/
│   │   └── SKILL.md          (被 skill 的"可用技能"列表引用)
│   ├── testing-debugging/
│   │   └── SKILL.md
│   ├── fastapi-development/
│   │   └── SKILL.md
│   ├── database-migration/
│   │   └── SKILL.md
│   ├── gitlab-search/
│   │   └── SKILL.md
│   ├── grill-me/
│   │   └── SKILL.md
│   ├── tdd/
│   │   └── SKILL.md
│   └── grill-with-docs/
│       └── SKILL.md
```

> 说明：`auto-task-execute` 与 `auto-task-verify` 的第一步都会读取 `.devin/skills/` 下所有相关 `SKILL.md`。如果只转发两个 skill，调用时会找不到依赖 skill。

### 2.2 项目级约定文件（接收方必须存在，内容可本地化）

| 文件路径 | 用途 | 是否必须 |
|---------|------|---------|
| `AGENTS.md` | 项目全貌、开发约定、命令说明 | 必须 |
| `.devin/settings.md` | Devin 项目级配置 | 必须 |
| `docs/document/task_list.md` | 任务清单，skill 的核心输入 | 必须 |
| `CONTEXT.md` | 项目结构和关键约定 | 可选，但强烈建议 |

### 2.3 工具链配置依赖（skill 执行验证时用到）

| 文件路径 | 用途 |
|---------|------|
| `requirements.txt` | Python 依赖清单 |
| `pyproject.toml` | `black`/`isort` 等工具配置 |
| `.flake8` | flake8 配置 |
| `pytest.ini` | pytest + xdist 配置 |

### 2.4 外部/基础设施依赖

- **GitLab MCP** 或 `gitlab-search` skill（接收方若不用 GitLab，可本地化为 `grep_search`/`read_file`）
- 项目代码仓库本身（用于文件勘察、代码搜索、核验）

---

## 3. 导出方操作清单

- [ ] 确认本项目中 `.devin/skills/auto-task-execute/SKILL.md` 与 `.devin/skills/auto-task-verify/SKILL.md` 存在且为最新版本。
- [ ] 将 `.devin/skills/` 下以下 10 个 skill 目录一起打包：
  - `auto-task-execute`
  - `auto-task-verify`
  - `python-development`
  - `testing-debugging`
  - `fastapi-development`
  - `database-migration`
  - `gitlab-search`
  - `grill-me`
  - `tdd`
  - `grill-with-docs`
- [ ] 将项目约定文件一起提供（供接收方参考/改造）：
  - `AGENTS.md`
  - `.devin/settings.md`
  - `docs/document/task_list.md`
  - `CONTEXT.md`（如有）
- [ ] 将工具链配置样例一起提供：
  - `requirements.txt`
  - `pyproject.toml`
  - `.flake8`
  - `pytest.ini`
- [ ] 向接收方说明：skill 中硬编码了 `C:\AIOps_Agent_bak` 路径，需要替换为接收方项目根目录。

### 3.1 快速打包脚本

#### PowerShell

```powershell
$src = "C:\AIOps_Agent_bak"
$dest = "$env:TEMP\skills_export"

$skills = @(
    "auto-task-execute",
    "auto-task-verify",
    "python-development",
    "testing-debugging",
    "fastapi-development",
    "database-migration",
    "gitlab-search",
    "grill-me",
    "tdd",
    "grill-with-docs"
)

# 复制 skill
New-Item -ItemType Directory -Force -Path "$dest\devin_skills" | Out-Null
foreach ($s in $skills) {
    Copy-Item -Path "$src\.devin\skills\$s" -Destination "$dest\devin_skills\$s" -Recurse -Force
}

# 复制项目约定和配置样例
$deps = @(
    "AGENTS.md",
    "CONTEXT.md",
    "docs\document\task_list.md",
    ".devin\settings.md",
    "requirements.txt",
    "pyproject.toml",
    ".flake8",
    "pytest.ini"
)
New-Item -ItemType Directory -Force -Path "$dest\project_deps" | Out-Null
foreach ($d in $deps) {
    if (Test-Path "$src\$d") {
        Copy-Item -Path "$src\$d" -Destination "$dest\project_deps\" -Force
    }
}

Compress-Archive -Path "$dest\*" -DestinationPath "$env:TEMP\aiops_skills_export.zip" -Force
Write-Host "已导出到: $env:TEMP\aiops_skills_export.zip"
```

#### Python

```python
import shutil
from pathlib import Path

src = Path(r"C:\AIOps_Agent_bak")
dest = Path(r"%TEMP%\skills_export").expanduser()

dest.mkdir(parents=True, exist_ok=True)

skills = [
    "auto-task-execute",
    "auto-task-verify",
    "python-development",
    "testing-debugging",
    "fastapi-development",
    "database-migration",
    "gitlab-search",
    "grill-me",
    "tdd",
    "grill-with-docs",
]

skills_dest = dest / "devin_skills"
skills_dest.mkdir(exist_ok=True)
for s in skills:
    shutil.copytree(
        src / ".devin" / "skills" / s,
        skills_dest / s,
        dirs_exist_ok=True,
    )

deps_dest = dest / "project_deps"
deps_dest.mkdir(exist_ok=True)
deps = [
    "AGENTS.md",
    "CONTEXT.md",
    "docs/document/task_list.md",
    ".devin/settings.md",
    "requirements.txt",
    "pyproject.toml",
    ".flake8",
    "pytest.ini",
]
for d in deps:
    p = src / d
    if p.exists():
        if p.is_file():
            shutil.copy2(p, deps_dest / p.name)
        else:
            shutil.copytree(p, deps_dest / p.name, dirs_exist_ok=True)

shutil.make_archive(str(dest), "zip", root_dir=dest.parent, base_dir=dest.name)
print(f"已导出到: {dest}.zip")
```

---

## 4. 接收方操作清单

### 4.1 环境要求

- 使用支持 Devin skills 的 IDE/客户端。
- Python 3.10+ 环境。
- 已安装 `requirements.txt` 中的工具链（`black`、`flake8`、`isort`、`mypy`、`pytest`、`pytest-xdist`、`bandit` 等）。

### 4.2 部署步骤

- [ ] 解压导出的压缩包。
- [ ] 将 `devin_skills/` 下的 10 个 skill 目录复制到自己项目的 `.devin/skills/` 下。
- [ ] 将 `project_deps/` 中的文件按需复制到项目根目录：
  - `AGENTS.md`
  - `.devin/settings.md`
  - `docs/document/task_list.md`
  - `CONTEXT.md`（可选）
  - `requirements.txt`
  - `pyproject.toml`
  - `.flake8`
  - `pytest.ini`
- [ ] 打开 `.devin/skills/auto-task-execute/SKILL.md` 与 `.devin/skills/auto-task-verify/SKILL.md`。
- [ ] 全文搜索并替换 `C:\AIOps_Agent_bak` 为接收方项目根目录（例如 `C:\MyProject`）。
- [ ] 如果不用 GitLab，将 `gitlab-search` 替换为本地 `grep_search`/`read_file`：
  - 搜索 `gitlab-search` / `GitLab MCP` / `gitlab_search` 等关键字。
  - 将涉及 `gitlab-search` 的步骤改写为使用 `grep_search` + `read_file`。
- [ ] 根据项目实际调整工具链命令：
  - `python -m black .`
  - `python -m flake8 .`
  - `python -m isort . --check-only` / `python -m isort .`
  - `python -m mypy .`
  - `pytest -n auto`
  - `pytest -n auto --collect-only`
  - `bandit -r .`
  - `safety check`
- [ ] 如果项目不用 `flake8` + `isort`，而使用 `ruff` 或其他工具，需要修改 skill 中“当前工具链约定”与“执行铁律”部分。
- [ ] 确保 `docs/document/task_list.md` 存在且格式与 skill 期望一致（任务编号、子任务、验收标准）。

### 4.3 验证步骤

- [ ] 在 IDE 中输入 `/auto-task-execute` 或 `/auto-task-verify`，确认 skill 能被识别并触发。
- [ ] 让 skill 执行第一步（建立真实上下文），确认它能成功读取 `AGENTS.md`、`.devin/settings.md`、`docs/document/task_list.md`、`CONTEXT.md`。
- [ ] 对一个小范围任务测试执行/核验流程，确认无文件读取失败或命令路径错误。
- [ ] 运行一次 lint 和测试命令，确认工具链配置与项目匹配。

---

## 5. 常见本地化改造点

| 改造项 | 示例 |
|-------|------|
| 项目路径 | `C:\AIOps_Agent_bak` → `C:\MyProject` |
| 任务清单路径 | `docs/document/task_list.md` → 实际路径 |
| GitLab 搜索 | 替换为本地 `grep_search` / `find_by_name` |
| Lint 工具 | `flake8` + `isort` → `ruff`（若项目使用） |
| 测试命令 | `pytest -n auto` → 其他并行参数 |
| 额外依赖 skill | 根据项目需要增删 `.devin/skills/` 下的 skill |
| 验证维度 | 调整 `auto-task-verify` 中的十维度核验内容 |

---

## 6. 注意事项

- **不要只转发两个 `SKILL.md` 文件**：它们依赖 `.devin/skills/` 下其他 skill，缺少依赖会导致调用失败。
- **不要忽略 `AGENTS.md` 与 `.devin/settings.md`**：这两个是 skill 第一步强制读取的文件，缺失会导致 skill 第一步就卡住。
- **`docs/document/task_list.md` 格式必须兼容**：skill 会基于该文件解析任务范围、描述和验收标准，格式不一致会导致任务识别失败。
- **GitLab MCP 不是必须的**：如果接收方没有 GitLab，可本地化为本地搜索工具，但需要在 `SKILL.md` 中显式替换。
- **命令约定需与项目匹配**：`black`/`flake8`/`isort`/`pytest` 等命令的参数与配置必须和接收方项目一致。

---

## 7. 最小可运行交付物

如果只想做最小转发，必须包含：

```
devin_skills/
├── auto-task-execute/SKILL.md
├── auto-task-verify/SKILL.md
├── python-development/SKILL.md
├── testing-debugging/SKILL.md
├── fastapi-development/SKILL.md
├── database-migration/SKILL.md
├── gitlab-search/SKILL.md
├── grill-me/SKILL.md
├── tdd/SKILL.md
└── grill-with-docs/SKILL.md
project_deps/
├── AGENTS.md
├── .devin/settings.md
├── docs/document/task_list.md
├── requirements.txt
├── pyproject.toml
├── .flake8
└── pytest.ini
```

以及一份说明：
- 替换 `C:\AIOps_Agent_bak` 为接收方项目根目录。
- 配置 GitLab MCP 或将 `gitlab-search` 替换为本地搜索。
- 对齐 lint/test 工具链。
