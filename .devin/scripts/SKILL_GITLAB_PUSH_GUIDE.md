# 将 `auto-task-execute` 与 `auto-task-verify` Skill 推送到 GitLab 分享指南

## 1. 能否推送到 GitLab 分享？

可以。本质上就是把 `.devin/skills/` 下的 skill 目录和必要的项目约定文件打包/推送到 GitLab，别人拉取后放到自己项目的 `.devin/skills/` 下即可使用。

**注意**：这两个 skill 为 `C:\AIOps_Agent_bak` 量身定制，别人使用前必须按 《`SKILL_TRANSFER_GUIDE.md`》 做本地化改造。

---

## 2. 推荐三种推送方式

| 方式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **方式 A：推到当前项目仓库的子目录** | 同事/团队成员共用同一项目 | 版本统一、与项目代码一起管理 | 非项目成员看不到 |
| **方式 B：新建独立 GitLab 仓库** | 跨团队/跨公司分享 | 权限灵活、可独立发版 | 接收方需手动拉取 |
| **方式 C：用 GitLab MCP / API 直接上传** | 不便于用 git CLI 时 | 不依赖本地 git 配置 | 需要项目 ID 和 Token |

---

## 3. 要推哪些文件？

### 3.1 必须推送的 Skill 文件（10 个 skill 目录）

```
.devin/skills/
├── auto-task-execute/
│   └── SKILL.md
├── auto-task-verify/
│   └── SKILL.md
├── python-development/
├── testing-debugging/
├── fastapi-development/
├── database-migration/
├── gitlab-search/
├── grill-me/
├── tdd/
└── grill-with-docs/
```

> 不能只推 `auto-task-execute` 和 `auto-task-verify`，它们第一步会读取 `.devin/skills/` 下其他 skill 文件。

### 3.2 建议一起推送的依赖文件（供接收方参考/改造）

```
AGENTS.md
CONTEXT.md
.devin/settings.md
docs/document/task_list.md
requirements.txt
pyproject.toml
.flake8
pytest.ini
```

### 3.3 建议一起推送的迁移文档

```
.devin/scripts/SKILL_TRANSFER_GUIDE.md
.devin/scripts/SKILL_GITLAB_PUSH_GUIDE.md  (本文件)
```

---

## 4. 方式 A：推到当前项目仓库的子目录

### 4.1 仓库结构

在现有 GitLab 仓库里建一个子目录，例如：

```
aiops-agent/
├── .devin/skills/                    # 本项目正在用的 skill
│   ├── auto-task-execute/
│   └── ...
└── share/skills/                     # 对外分享的 skill 包
    ├── auto-task-execute/
    ├── auto-task-verify/
    ├── python-development/
    ├── ...
    ├── project_deps/
    │   ├── AGENTS.md
    │   ├── .devin/settings.md
    │   ├── docs/document/task_list.md
    │   ├── requirements.txt
    │   ├── pyproject.toml
    │   ├── .flake8
    │   └── pytest.ini
    └── README.md
```

### 4.2 推送步骤

```powershell
# 1. 在仓库根目录创建分享目录
$repo = "C:\AIOps_Agent_bak"
$share = "$repo\share\skills"
New-Item -ItemType Directory -Force -Path $share | Out-Null

# 2. 复制 skill（保持原目录结构）
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
foreach ($s in $skills) {
    Copy-Item -Path "$repo\.devin\skills\$s" -Destination "$share\$s" -Recurse -Force
}

# 3. 复制项目依赖样例
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
New-Item -ItemType Directory -Force -Path "$share\project_deps" | Out-Null
foreach ($d in $deps) {
    if (Test-Path "$repo\$d") {
        Copy-Item -Path "$repo\$d" -Destination "$share\project_deps\" -Force
    }
}

# 4. 提交并推送（确保在 git 仓库中执行）
git add share/skills
git commit -m "chore: share auto-task-execute and auto-task-verify skills"
git push origin main
```

---

## 5. 方式 B：新建独立 GitLab 仓库

### 5.1 新建仓库

在 GitLab 上新建一个项目，例如 `aiops-agent-skills`。

### 5.2 本地初始化并推送

```powershell
$repoRoot = "C:\AIOps_Agent_bak"
$shareRoot = "$env:TEMP\aiops-agent-skills"
New-Item -ItemType Directory -Force -Path $shareRoot | Out-Null
Set-Location -Path $shareRoot

git init
git remote add origin https://gitlab.dell.com/your-group/aiops-agent-skills.git

# 复制 skill 和依赖文件（同方式 A 的步骤）
# ...

git add .
git commit -m "feat: init shared devin skills"
git push -u origin main
```

### 5.3 仓库推荐结构

```
aiops-agent-skills/
├── .devin/skills/              # 接收方可以直接复制到自己项目
│   ├── auto-task-execute/
│   ├── auto-task-verify/
│   └── ...
├── project_deps/               # 项目约定和配置样例
│   ├── AGENTS.md
│   ├── settings.md
│   ├── task_list.md
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── .flake8
│   └── pytest.ini
├── README.md                   # 使用说明
└── CHANGELOG.md                # 版本变更
```

---

## 6. 方式 C：用 GitLab MCP / API 直接上传

适用于不方便使用 git CLI 的场景。需要：

- GitLab API URL（当前配置：`https://gitlab.dell.com/api/v4`）
- Personal Access Token（已在 `mcp_config.json` 配置，不要直接写入代码）
- GitLab 项目 ID 或 `namespace/project` 路径

### 6.1 Python 上传脚本（基于 GitLab API）

```python
"""Upload shared skills to GitLab repository via API.

Usage:
    python scripts/upload_skills_to_gitlab.py --project "your-group/aiops-agent-skills" --branch main
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

import requests

GITLAB_API_URL = os.environ.get("GITLAB_API_URL", "https://gitlab.dell.com/api/v4")
GITLAB_TOKEN = os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN")

SRC = Path(r"C:\AIOps_Agent_bak")
SKILLS = [
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
DEPS = [
    "AGENTS.md",
    "CONTEXT.md",
    "docs/document/task_list.md",
    ".devin/settings.md",
    "requirements.txt",
    "pyproject.toml",
    ".flake8",
    "pytest.ini",
]


def gitlab_path(local_path: Path) -> str:
    """Convert local path to GitLab repository path prefix."""
    relative = local_path.relative_to(SRC).as_posix()
    return f"share/skills/{relative}"


def upload_file(project: str, branch: str, git_path: str, content: bytes, message: str):
    """Upload or update a single file in GitLab repository."""
    url = f"{GITLAB_API_URL}/projects/{requests.utils.quote(project, safe='')}/repository/files/{requests.utils.quote(git_path, safe='')}"
    data = {
        "branch": branch,
        "content": base64.b64encode(content).decode(),
        "commit_message": message,
        "encoding": "base64",
    }
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN, "Content-Type": "application/json"}

    # Try create first, then update if exists
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code == 409:
        resp = requests.put(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Upload skills to GitLab")
    parser.add_argument("--project", required=True, help="GitLab project path or ID")
    parser.add_argument("--branch", default="main", help="Target branch")
    args = parser.parse_args()

    if not GITLAB_TOKEN:
        print("Error: GITLAB_PERSONAL_ACCESS_TOKEN is not set", file=sys.stderr)
        sys.exit(1)

    # Collect all files to upload
    files = []
    for skill in SKILLS:
        skill_dir = SRC / ".devin" / "skills" / skill
        if not skill_dir.exists():
            print(f"Warning: skill dir not found: {skill_dir}", file=sys.stderr)
            continue
        for p in skill_dir.rglob("*"):
            if p.is_file():
                files.append((p, gitlab_path(p)))

    for dep in DEPS:
        p = SRC / dep
        if p.exists():
            files.append((p, f"share/skills/project_deps/{p.name}"))

    # Upload files one by one
    for local_path, git_path in files:
        print(f"Uploading {git_path} ...")
        upload_file(
            args.project,
            args.branch,
            git_path,
            local_path.read_bytes(),
            f"feat: add {git_path}",
        )

    print(f"Uploaded {len(files)} files to {args.project} on branch {args.branch}")


if __name__ == "__main__":
    main()
```

### 6.2 运行方式

```powershell
$env:GITLAB_API_URL = "https://gitlab.dell.com/api/v4"
$env:GITLAB_PERSONAL_ACCESS_TOKEN = "your-token"  # 不要硬编码
python scripts/upload_skills_to_gitlab.py --project "your-group/aiops-agent-skills" --branch main
```

---

## 7. 接收方使用方式

无论用哪种方式推送，接收方拿到后的步骤都一样：

1. **克隆/拉取仓库** 或下载 skill 压缩包。
2. **复制 skill 目录** 到自己项目的 `.devin/skills/` 下。
3. **复制项目依赖样例**（`AGENTS.md`、`.devin/settings.md`、`docs/document/task_list.md` 等）并做本地化改造。
4. **修改 `SKILL.md` 中的项目路径**：把 `C:\AIOps_Agent_bak` 替换为接收方项目根目录。
5. **配置 GitLab MCP 或替换为本地搜索工具**。
6. **在 Devin IDE 输入 `/auto-task-execute` 或 `/auto-task-verify`** 验证是否能正常触发。

---

## 8. 推送前检查清单

- [ ] 确认 `GITLAB_PERSONAL_ACCESS_TOKEN` 已设置且有效。
- [ ] 确认 GitLab 项目路径/ID 正确。
- [ ] 确认推送的 skill 目录包含全部 10 个 skill。
- [ ] 确认项目依赖样例文件已一起推送。
- [ ] 确认没有推送敏感文件（如 `mcp_config.json`、`.env`、数据库密码等）。
- [ ] 确认 `SKILL.md` 中的 `C:\AIOps_Agent_bak` 路径保留，由接收方自行替换。
- [ ] 如果推到公开仓库，确认没有包含公司内部私有代码。
- [ ] 更新 `README.md`，说明如何使用和本地化改造。

---

## 9. 安全提醒

- **不要** 将 `GITLAB_PERSONAL_ACCESS_TOKEN` 写入任何代码文件或提交到仓库。
- 当前 token 存储在 `C:\Users\Hualong_Chen\AppData\Roaming\devin\mcp_config.json`，请确保该文件不在 `.gitignore` 之外被提交。
- 如果分享对象是团队外人员，建议新建独立仓库并设置访问权限。
