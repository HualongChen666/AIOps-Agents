#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Devin IDE 配置初始化脚本
确保配置在新session中能够正确加载
"""

import json
import os
import shutil
import sys
from pathlib import Path


def create_global_config_backup():
    """创建全局配置备份，确保跨session可用"""
    # Windows用户级别配置路径
    if sys.platform == "win32":
        global_config_dir = Path(os.path.expandvars(r"%APPDATA%\devin"))
    else:
        global_config_dir = Path.home() / ".config" / "devin"

    global_config_dir.mkdir(parents=True, exist_ok=True)

    # 复制项目配置到全局配置
    project_config = Path(".devin/config.json")
    global_config = global_config_dir / "config.json"

    if project_config.exists():
        shutil.copy2(project_config, global_config)
        print(f"✅ 全局配置已创建: {global_config}")
        return True
    else:
        print(f"❌ 项目配置不存在: {project_config}")
        return False


def verify_skills_structure():
    """验证skills目录结构"""
    skills_dir = Path(".devin/skills")

    if not skills_dir.exists():
        print("❌ Skills目录不存在")
        return False

    required_skills = [
        "auto-task-execute",
        "auto-task-verify",
        "database-migration",
        "fastapi-development",
        "gitlab-search",
        "grill-me",
        "grill-with-docs",
        "python-development",
        "tdd",
        "testing-debugging",
    ]

    all_valid = True
    for skill_name in required_skills:
        skill_path = skills_dir / skill_name / "SKILL.md"
        if skill_path.exists():
            print(f"✅ Skill: {skill_name}")
        else:
            print(f"❌ Skill缺失: {skill_name}")
            all_valid = False

    return all_valid


def verify_rules_structure():
    """验证rules目录结构"""
    rules_dir = Path(".devin/rules")

    if not rules_dir.exists():
        print("❌ Rules目录不存在")
        return False

    required_rules = ["python-rules.md", "fastapi-rules.md", "project-conventions.md"]

    all_valid = True
    for rule_file in required_rules:
        rule_path = rules_dir / rule_file
        if rule_path.exists():
            print(f"✅ Rule: {rule_file}")
        else:
            print(f"❌ Rule缺失: {rule_file}")
            all_valid = False

    return all_valid


def create_session_check_file():
    """创建session检查文件，用于验证配置加载"""
    check_file = Path(".devin/.session_check")
    check_file.write_text(f"Session initialized at: {os.getcwd()}\n")
    print(f"✅ Session检查文件已创建: {check_file}")


def verify_mcp_config():
    """验证MCP配置"""
    config_file = Path(".devin/config.json")
    local_config_file = Path(".devin/config.local.json")

    if not config_file.exists():
        print("❌ 主配置文件不存在")
        return False

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 验证项目目录配置
        if "project" in config:
            project_dir = config["project"].get("directory", "")
            expected_dir = r"C:\AIOps_Agent_bak"
            if project_dir == expected_dir:
                print(f"✅ 项目目录配置正确: {project_dir}")
            else:
                print(f"⚠️ 项目目录配置不匹配: {project_dir} != {expected_dir}")

        # 验证GitLab上传控制
        if "security" in config and "gitlab_upload_control" in config["security"]:
            upload_control = config["security"]["gitlab_upload_control"]
            if upload_control.get("enabled") and upload_control.get(
                "deny_all_uploads_without_command"
            ):
                print("✅ GitLab上传控制已启用")
                print(f"   上传指令模式: {upload_control.get('allowed_command_pattern', 'N/A')}")
            else:
                print("⚠️ GitLab上传控制未正确配置")

        if "mcpServers" not in config:
            print("❌ MCP服务器配置缺失")
            return False

        print(f"✅ MCP服务器数量: {len(config['mcpServers'])}")

        # 检查GitLab配置
        if "gitlab" in config["mcpServers"]:
            print("✅ GitLab MCP已配置")

        # 检查权限配置
        if "permissions" in config:
            permissions = config["permissions"]
            denied_ops = permissions.get("deny", [])
            if any("upload" in op or "push" in op for op in denied_ops):
                print("✅ GitLab上传权限已限制")

        # 检查本地配置
        if local_config_file.exists():
            with open(local_config_file, "r", encoding="utf-8") as f:
                local_config = json.load(f)
            if "gitlab" in local_config.get("mcpServers", {}):
                gitlab_env = local_config["mcpServers"]["gitlab"]["env"]
                token = gitlab_env.get("GITLAB_PERSONAL_ACCESS_TOKEN", "")
                if token and not token.startswith("YOUR_"):
                    print("✅ GitLab Token已配置")
                else:
                    print("⚠️ GitLab Token需要配置")

        return True

    except json.JSONDecodeError as e:
        print(f"❌ 配置文件JSON格式错误: {e}")
        return False


def create_devin_ignore():
    """创建.devinignore文件，确保配置文件被正确处理"""
    devin_ignore = Path(".devinignore")

    ignore_content = """# Devin IDE ignore file
# Ensure sensitive configs are not committed

.env
.env.local
*.key
*.pem
credentials.json
secrets/
"""

    if not devin_ignore.exists():
        devin_ignore.write_text(ignore_content, encoding="utf-8")
        print("✅ .devinignore file created")
    else:
        print("✅ .devinignore file already exists")


def main():
    """主函数"""
    import sys

    if sys.platform == "win32":
        import codecs

        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

    print("🚀 Devin IDE 配置初始化")
    print("=" * 50)

    # 验证当前目录
    if not Path(".devin").exists():
        print("❌ 当前目录不是Devin项目目录")
        sys.exit(1)

    print("\n📋 配置验证:")

    # 验证MCP配置
    mcp_ok = verify_mcp_config()

    # 验证Skills结构
    print("\n🎯 Skills验证:")
    skills_ok = verify_skills_structure()

    # 验证Rules结构
    print("\n📐 Rules验证:")
    rules_ok = verify_rules_structure()

    # 创建全局配置备份
    print("\n🌐 全局配置:")
    global_ok = create_global_config_backup()

    # 创建session检查文件
    create_session_check_file()

    # 创建devinignore
    create_devin_ignore()

    print("\n" + "=" * 50)

    if all([mcp_ok, skills_ok, rules_ok, global_ok]):
        print("✅ 配置初始化完成!")
        print("\n📝 下一步:")
        print("1. 重启Devin IDE")
        print("2. 运行 'devin mcp list' 验证MCP服务器")
        print("3. 测试技能: /python-development test")
        print("4. 测试自动任务: /auto-task-execute 任务1~任务5")
        print("5. 新session会自动加载这些配置")
    else:
        print("⚠️ 部分配置验证失败，请检查上述错误")
        sys.exit(1)


if __name__ == "__main__":
    main()
