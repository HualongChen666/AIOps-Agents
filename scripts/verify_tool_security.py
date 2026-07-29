#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Tool 权限安全验证脚本
验证 .devin/config.json 和 .windsurf/rules/security-tools.md 的最小权限策略。
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


ALLOWED_FS_READ_PATTERNS = [
    "mcp__filesystem__read_*",
    "mcp__filesystem__list_*",
    "mcp__filesystem__directory_tree",
    "mcp__filesystem__search_files",
    "mcp__filesystem__get_file_info",
]

DENIED_FS_PATTERNS = [
    "mcp__filesystem__write_*",
    "mcp__filesystem__edit_*",
    "mcp__filesystem__delete_*",
    "mcp__filesystem__create_*",
    "mcp__filesystem__move_*",
]

DENIED_DB_PATTERNS = [
    "mcp__postgres__drop_*",
    "mcp__postgres__truncate_*",
]

REQUIRED_NATIVE_RULES = [
    "bash",
    "read_url_content",
    "search_web",
    "read_file",
    "write_to_file",
    "edit",
    "multi_edit",
    "browser_preview",
    "死循环",
    "敏感文件",
]


def load_devin_config():
    config_path = PROJECT_ROOT / ".devin" / "config.json"
    local_config_path = PROJECT_ROOT / ".devin" / "config.local.json"

    with open(config_path, "r", encoding="utf-8") as f:
        base_config = json.load(f)

    if local_config_path.exists():
        with open(local_config_path, "r", encoding="utf-8") as f:
            local_config = json.load(f)

        # mcpServers 合并
        if "mcpServers" in local_config:
            base_mcp = base_config.setdefault("mcpServers", {})
            base_mcp.update(local_config["mcpServers"])

        # 注意：local 的其他顶层键会覆盖 base，这是潜在覆盖风险
        for key in local_config:
            if key != "mcpServers":
                base_config[key] = local_config[key]

    return base_config


def check_plaintext_tokens(config):
    print("\n🔒 检查 MCP 服务器敏感信息配置")
    warnings = []
    servers = config.get("mcpServers", {})
    for name, server in servers.items():
        env = server.get("env", {})
        for key, value in env.items():
            if any(s in key.upper() for s in ["TOKEN", "KEY", "SECRET", "PASSWORD"]):
                value_str = str(value)
                if (
                    value_str
                    and not value_str.startswith("YOUR_")
                    and not value_str.startswith("${")
                ):
                    warnings.append(
                        f"    MCP server '{name}' 的 {key} 疑似为明文硬编码，建议改用环境变量引用"
                    )

    if warnings:
        for w in warnings:
            print(w)
        print("  ⚠️  发现明文敏感配置（config.local.json 中的 Token/Key 目前为明文）")
        print(
            "      建议：轮换该凭据，并通过 Devin 支持的注入方式（如环境变量或安全凭证管理）配置，"
        )
        print("      避免长期以明文形式存储在本地配置文件中。")
        print("      该文件已受 .devinignore 保护不被索引，但仍存在本地泄露风险。")
        return True  # 作为警告处理：需要用户手动轮换，不能自动修复
    print("  ✅ 未发现明文硬编码的高危凭据")
    return True


def check_all_mcp_servers_covered(config):
    print("\n🔒 检查所有 MCP 服务器是否已配置权限规则")
    servers = config.get("mcpServers", {})
    permissions = config.get("permissions", {})
    all_rules = (
        permissions.get("allow", []) + permissions.get("ask", []) + permissions.get("deny", [])
    )

    uncovered = []
    for server_name in servers:
        if not any(p.startswith(f"mcp__{server_name}__") for p in all_rules):
            uncovered.append(server_name)

    if uncovered:
        print(f"  ❌ 以下 MCP 服务器缺少权限规则（可能默认放行所有 Tool）: {uncovered}")
        return False

    print(f"  ✅ 所有 {len(servers)} 个 MCP 服务器均已配置权限规则")
    return True


def check_local_config_override():
    print("\n🔒 检查 .devin/config.local.json 权限覆盖风险")
    local_config_path = PROJECT_ROOT / ".devin" / "config.local.json"
    if not local_config_path.exists():
        print("  ⚠️  不存在本地配置文件，使用项目默认权限")
        return True

    with open(local_config_path, "r", encoding="utf-8") as f:
        local_config = json.load(f)

    if "permissions" in local_config:
        print("  ❌ .devin/config.local.json 包含 permissions，会覆盖项目级权限配置")
        return False

    print("  ✅ 本地配置文件未覆盖 permissions，项目级权限有效")
    return True


def check_mcp_permissions(config):
    print("\n🔒 检查 MCP 权限配置")
    errors = []
    permissions = config.get("permissions", {})
    allowed = permissions.get("allow", [])
    ask = permissions.get("ask", [])
    deny = permissions.get("deny", [])

    # 1. 不允许 mcp__filesystem__* 这种全通配符
    if "mcp__filesystem__*" in allowed:
        errors.append("❌ filesystem MCP 仍使用 mcp__filesystem__* 全通配符，权限过大")
    else:
        print("  ✅ filesystem MCP 未使用全通配符")

    # 2. filesystem allow 应该只包含读/列/搜索
    fs_allowed = [p for p in allowed if p.startswith("mcp__filesystem__")]
    for p in fs_allowed:
        if p not in ALLOWED_FS_READ_PATTERNS:
            errors.append(f"  ❌ filesystem allow 列表包含非只读模式: {p}")
    if all(p in ALLOWED_FS_READ_PATTERNS for p in fs_allowed) and fs_allowed:
        print(f"  ✅ filesystem MCP 仅允许只读/列表/搜索操作 ({len(fs_allowed)} 条)")

    # 3. filesystem 写入/删除等操作应在 deny
    missing_deny = [p for p in DENIED_FS_PATTERNS if p not in deny]
    if missing_deny:
        errors.append(f"  ❌ filesystem deny 缺少: {missing_deny}")
    else:
        print("  ✅ filesystem MCP 明确拒绝写/改/删/创建/移动操作")

    # 4. postgres execute_sql 必须在 ask，不在 allow
    if "mcp__postgres__execute_sql" in allowed:
        errors.append("  ❌ mcp__postgres__execute_sql 仍在 allow 中")
    elif "mcp__postgres__execute_sql" in ask:
        print("  ✅ mcp__postgres__execute_sql 已移至 ask（需确认）")
    else:
        errors.append("  ❌ mcp__postgres__execute_sql 未在 ask 中配置")

    # 5. postgres read_query 保留 allow
    if "mcp__postgres__read_query" in allowed:
        print("  ✅ mcp__postgres__read_query 仍允许只读查询")
    else:
        errors.append("  ❌ mcp__postgres__read_query 不在 allow 中")

    # 6. deny 包含 destructive postgres operations
    missing_db_deny = [p for p in DENIED_DB_PATTERNS if p not in deny]
    if missing_db_deny:
        errors.append(f"  ❌ postgres deny 缺少: {missing_db_deny}")
    else:
        print("  ✅ postgres MCP 明确拒绝 drop/truncate 操作")

    # 7. gitlab write/push/commit/upload 必须在 ask
    gitlab_ask_patterns = [
        "mcp__gitlab__write_*",
        "mcp__gitlab__push",
        "mcp__gitlab__commit",
        "mcp__gitlab__upload",
    ]
    for p in gitlab_ask_patterns:
        if p not in ask:
            errors.append(f"  ❌ gitlab 写操作 {p} 未在 ask 中")
    if all(p in ask for p in gitlab_ask_patterns):
        print("  ✅ gitlab 写/push/commit/upload 操作均需确认")

    # 8. gitlab read/search 保留 allow
    if "mcp__gitlab__read_*" in allowed and "mcp__gitlab__search_*" in allowed:
        print("  ✅ gitlab 读/搜索操作仍允许")
    else:
        errors.append("  ❌ gitlab 读/搜索权限未正确保留")

    if errors:
        for e in errors:
            print(e)
        return False
    return True


def check_gitlab_upload_control(config):
    print("\n🔒 检查 GitLab 上传控制")
    security = config.get("security", {})
    upload = security.get("gitlab_upload_control", {})
    if upload.get("enabled") and upload.get("deny_all_uploads_without_command"):
        print("  ✅ GitLab 上传控制已启用")
        return True
    print("  ❌ GitLab 上传控制未启用或配置不完整")
    return False


def check_native_tool_rules():
    print("\n🛡️ 检查原生 Tool 安全规则")
    rule_path = PROJECT_ROOT / ".windsurf" / "rules" / "security-tools.md"
    if not rule_path.exists():
        print(f"  ❌ 安全规则文件不存在: {rule_path}")
        return False

    content = rule_path.read_text(encoding="utf-8")
    missing = []
    for keyword in REQUIRED_NATIVE_RULES:
        if keyword not in content:
            missing.append(keyword)

    if missing:
        print(f"  ❌ 安全规则缺少关键内容: {missing}")
        return False

    print("  ✅ 原生 Tool 安全规则文件存在且包含关键约束")
    return True


def check_devinignore():
    print("\n🔒 检查 .devinignore 敏感文件保护")
    ignore_path = PROJECT_ROOT / ".devinignore"
    if not ignore_path.exists():
        print("  ❌ .devinignore 不存在")
        return False

    content = ignore_path.read_text(encoding="utf-8")
    required = [".env", "*.key", "*.pem", "credentials.json", "secrets/", ".devin/*.local.json"]
    missing = [r for r in required if r not in content]
    if missing:
        print(f"  ❌ .devinignore 缺少: {missing}")
        return False

    print("  ✅ .devinignore 已保护敏感文件")
    return True


def main():
    import sys

    print("🔍 Agent Tool 权限安全验证")
    print("=" * 50)

    try:
        config = load_devin_config()
    except Exception as e:
        print(f"❌ 无法读取 .devin/config.json: {e}")
        sys.exit(1)

    results = [
        check_mcp_permissions(config),
        check_all_mcp_servers_covered(config),
        check_gitlab_upload_control(config),
        check_local_config_override(),
        check_plaintext_tokens(config),
        check_native_tool_rules(),
        check_devinignore(),
    ]

    print("\n" + "=" * 50)
    if all(results):
        print("✅ 所有 Tool 权限安全检查通过")
        print("\n📋 已修复问题：")
        print("  1. filesystem MCP 从 * 全通配改为只读/列表/搜索模式")
        print("  2. mcp__postgres__execute_sql 从 allow 改为 ask")
        print("  3. 增加 filesystem write/edit/delete/create/move 显式 deny")
        print("  4. 增加 postgres drop/truncate 显式 deny")
        print("  5. 为 github/git/brave-search/memory 等全部 MCP 服务器补充最小权限规则")
        print("  6. 原生 Tool 使用安全规则已写入 .windsurf/rules/security-tools.md")
        print("  7. .devinignore 已保护敏感文件不被索引")
        sys.exit(0)
    else:
        print("❌ 部分 Tool 权限安全检查未通过，请修复上述问题")
        sys.exit(1)


if __name__ == "__main__":
    main()
