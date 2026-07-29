#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Devin IDE 配置验证脚本
检查 MCP 服务器配置和 Skills 是否正确设置
"""

import json
import os
from pathlib import Path


def check_file_exists(filepath, description):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")  # noqa: F541
        return True
    else:
        print(f"❌ {description} 未找到: {filepath}")  # noqa: F541
        return False


def check_json_config(filepath, description):
    """检查 JSON 配置文件格式"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)
        print(f"✅ {description} 格式正确")  # noqa: F541
        return config
    except json.JSONDecodeError as e:
        print(f"❌ {description} JSON 格式错误: {e}")  # noqa: F541
        return None
    except Exception as e:
        print(f"❌ {description} 读取错误: {e}")  # noqa: F541
        return None


def merge_configs(base_config, local_config):
    """合并基础配置和本地配置"""
    if not base_config:
        return local_config
    if not local_config:
        return base_config

    merged = base_config.copy()

    # 合并 mcpServers
    if "mcpServers" in local_config:
        if "mcpServers" not in merged:
            merged["mcpServers"] = {}
        merged["mcpServers"].update(local_config["mcpServers"])

    # 合并其他字段
    for key in local_config:
        if key != "mcpServers":
            merged[key] = local_config[key]

    return merged


def check_mcp_servers(config):
    """检查 MCP 服务器配置"""
    if not config or "mcpServers" not in config:
        print("❌ MCP 服务器配置未找到")
        return False

    servers = config["mcpServers"]
    print(f"📋 配置的 MCP 服务器: {len(servers)} 个")  # noqa: F541

    required_fields = ["command", "args"]
    for server_name, server_config in servers.items():
        print(f"\n  🔧 {server_name}:")  # noqa: F541

        # 检查必需字段
        missing_fields = [field for field in required_fields if field not in server_config]
        if missing_fields:
            print(f"    ❌ 缺少字段: {missing_fields}")  # noqa: F541
            continue

        print(f"    ✅ 命令: {server_config['command']}")  # noqa: F541
        print(f"    ✅ 参数: {' '.join(server_config['args'])}")  # noqa: F541

        # 检查环境变量
        if "env" in server_config:
            env = server_config["env"]
            if env:
                print(f"    📝 环境变量: {len(env)} 个")  # noqa: F541
                for key, value in env.items():
                    # 检查是否为占位符
                    placeholder_patterns = ["YOUR_", "your_", "default_value"]
                    is_placeholder = any(pattern in str(value) for pattern in placeholder_patterns)

                    if is_placeholder:
                        print(f"      ⚠️  {key}: 需要配置 (当前: {value})")  # noqa: F541
                    else:
                        # 对于敏感信息，只显示部分内容
                        if "TOKEN" in key or "KEY" in key or "SECRET" in key:
                            masked_value = str(value)[:8] + "..." if len(str(value)) > 8 else "***"
                            print(f"      ✅ {key}: 已配置 ({masked_value})")  # noqa: F541
                        else:
                            print(f"      ✅ {key}: {value}")  # noqa: F541
            else:
                print(f"    📝 环境变量: 无")  # noqa: F541

    return True


def check_skills_directory():
    """检查 Skills 目录"""
    skills_dir = Path(".devin/skills")
    if not skills_dir.exists():
        print("❌ Skills 目录不存在")
        return False

    skill_files = list(skills_dir.glob("*/SKILL.md"))
    print(f"📚 找到 {len(skill_files)} 个 Skills:")  # noqa: F541

    for skill_file in skill_files:
        skill_name = skill_file.parent.name
        print(f"  ✅ {skill_name}")  # noqa: F541

        # 检查 SKILL.md 格式
        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()
                if content.startswith("---"):
                    print(f"    ✅ 包含 frontmatter")  # noqa: F541
                else:
                    print(f"    ⚠️  缺少 frontmatter")  # noqa: F541
        except Exception as e:
            print(f"    ❌ 读取错误: {e}")  # noqa: F541

    return True


def check_permissions(config):
    """检查权限配置，验证最小权限原则"""
    if not config or "permissions" not in config:
        print("⚠️  未配置权限")
        return True

    permissions = config["permissions"]
    print(f"\n🔒 权限配置:")  # noqa: F541

    allowed = permissions.get("allow", [])
    denied = permissions.get("deny", [])
    asked = permissions.get("ask", [])

    if "allow" in permissions:
        print(f"  ✅ 允许: {len(allowed)} 条规则")  # noqa: F541

    if "deny" in permissions:
        print(f"  ❌ 拒绝: {len(denied)} 条规则")  # noqa: F541

    if "ask" in permissions:
        print(f"  ❓ 询问: {len(asked)} 条规则")  # noqa: F541

    # 最小权限校验
    errors = []
    if "mcp__filesystem__*" in allowed:
        errors.append("    filesystem MCP 使用全通配符，权限过大")

    fs_write_denied = any(p.startswith("mcp__filesystem__write_") for p in denied)
    fs_delete_denied = any(p.startswith("mcp__filesystem__delete_") for p in denied)
    if not fs_write_denied or not fs_delete_denied:
        errors.append("    filesystem MCP 未显式拒绝写/删操作")

    if "mcp__postgres__execute_sql" in allowed:
        errors.append("    mcp__postgres__execute_sql 仍在 allow 中")
    elif "mcp__postgres__execute_sql" not in asked:
        errors.append("    mcp__postgres__execute_sql 未配置为 ask")

    if errors:
        for e in errors:
            print(f"  ❌ {e}")  # noqa: F541
        return False

    print("  ✅ 最小权限策略检查通过")  # noqa: F541
    return True


def main():
    """主函数"""
    import sys

    if sys.platform == "win32":
        import codecs

        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

    print("🔍 Devin IDE 配置验证")
    print("=" * 50)

    # 检查配置文件
    print("\n📁 检查配置文件:")
    config_exists = check_file_exists(".devin/config.json", "项目配置")
    local_config_exists = check_file_exists(".devin/config.local.json", "本地配置")

    if not config_exists:
        print("\n❌ 基础配置文件缺失，请先创建 .devin/config.json")
        sys.exit(1)

    # 检查配置格式
    print("\n📋 检查配置格式:")
    config = check_json_config(".devin/config.json", "项目配置")

    if local_config_exists:
        local_config = check_json_config(".devin/config.local.json", "本地配置")
    else:
        local_config = None
        print("⚠️  本地配置文件不存在 (可选)")

    # 合并配置
    if config and local_config:
        print("\n🔗 合并配置:")
        merged_config = merge_configs(config, local_config)
        print("✅ 配置合并完成")
    else:
        merged_config = config or local_config

    # 检查 MCP 服务器
    print("\n🔧 检查 MCP 服务器:")
    if merged_config:
        check_mcp_servers(merged_config)

    # 检查 Skills
    print("\n📚 检查 Skills:")
    check_skills_directory()

    # 检查权限
    print("\n🔒 检查权限配置:")
    if merged_config:
        check_permissions(merged_config)

    # 检查文档
    print("\n📖 检查文档:")
    check_file_exists(".devin/README.md", "配置说明")
    check_file_exists("AGENTS.md", "项目配置")

    print("\n" + "=" * 50)
    print("✅ 配置验证完成!")
    print("\n📝 下一步:")
    if local_config and "gitlab" in local_config.get("mcpServers", {}):
        gitlab_config = local_config["mcpServers"]["gitlab"]
        gitlab_url = gitlab_config["env"].get("GITLAB_URL", "")
        if gitlab_url and "YOUR_" not in gitlab_url:
            print("✅ GitLab 配置已完成")
            print(f"   - GitLab URL: {gitlab_url}")  # noqa: F541
            print(
                f"   - Token: {gitlab_config['env'].get('GITLAB_TOKEN', '')[:8]}..."
            )  # noqa: F541
        else:
            print("1. 编辑 .devin/config.local.json 配置 API 密钥")
            print("   - GITLAB_TOKEN: 你的 GitLab Personal Access Token")
            print("   - GITLAB_URL: 你的 GitLab 实例 URL (如 https://gitlab.com)")
    else:
        print("1. 编辑 .devin/config.local.json 配置 API 密钥")
        print("   - GITLAB_TOKEN: 你的 GitLab Personal Access Token")
        print("   - GITLAB_URL: 你的 GitLab 实例 URL (如 https://gitlab.com)")

    print("2. 重启 Devin IDE")
    print("3. 运行 'devin mcp list' 验证 MCP 服务器")
    print("4. 使用技能开始开发")


if __name__ == "__main__":
    main()
