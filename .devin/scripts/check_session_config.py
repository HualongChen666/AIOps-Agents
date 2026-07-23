#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Devin IDE Session配置检查脚本
用于在新session中验证配置是否正确加载
"""

import json
from pathlib import Path


def check_project_config():
    """检查项目级别配置"""
    print("📁 项目级别配置检查:")

    config_path = Path(".devin/config.json")
    if config_path.exists():
        print(f"✅ 项目配置文件存在: {config_path}")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            print("✅ 配置文件格式正确")
            print(f"   MCP服务器数量: {len(config.get('mcpServers', {}))}")

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
                    print(
                        f"   上传指令要求: {upload_control.get('allowed_command_pattern', 'N/A')}"
                    )
                else:
                    print("⚠️ GitLab上传控制未正确配置")

            return True
        except Exception as e:
            print(f"❌ 配置文件读取失败: {e}")
            return False
    else:
        print(f"❌ 项目配置文件不存在: {config_path}")
        return False


def check_local_config():
    """检查本地配置"""
    print("\n🔒 本地配置检查:")

    local_config_path = Path(".devin/config.local.json")
    if local_config_path.exists():
        print(f"✅ 本地配置文件存在: {local_config_path}")
        try:
            with open(local_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            print("✅ 本地配置文件格式正确")

            # 检查敏感信息配置
            if "mcpServers" in config:
                if "gitlab" in config["mcpServers"]:
                    gitlab_env = config["mcpServers"]["gitlab"]["env"]
                    token = gitlab_env.get("GITLAB_PERSONAL_ACCESS_TOKEN", "")
                    if token and not token.startswith("YOUR_"):
                        print("✅ GitLab Token已配置")
                    else:
                        print("⚠️ GitLab Token需要配置")
            return True
        except Exception as e:
            print(f"❌ 本地配置文件读取失败: {e}")
            return False
    else:
        print(f"⚠️ 本地配置文件不存在 (可选): {local_config_path}")
        return True  # 本地配置是可选的


def check_skills():
    """检查Skills配置"""
    print("\n🎯 Skills检查:")

    skills_dir = Path(".devin/skills")
    if not skills_dir.exists():
        print(f"❌ Skills目录不存在: {skills_dir}")
        return False

    skill_count = 0
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                print(f"✅ Skill: {skill_dir.name}")
                skill_count += 1
            else:
                print(f"❌ Skill文件缺失: {skill_dir.name}")

    print(f"📊 总计Skills: {skill_count}")
    return skill_count > 0


def check_rules():
    """检查Rules配置"""
    print("\n📐 Rules检查:")

    rules_dir = Path(".devin/rules")
    if not rules_dir.exists():
        print(f"❌ Rules目录不存在: {rules_dir}")
        return False

    rule_count = 0
    for rule_file in rules_dir.glob("*.md"):
        if rule_file.name != "README.md":
            print(f"✅ Rule: {rule_file.name}")
            rule_count += 1

    print(f"📊 总计Rules: {rule_count}")
    return rule_count > 0


def check_session_file():
    """检查Session初始化文件"""
    print("\n🔄 Session检查:")

    session_check = Path(".devin/.session_check")
    if session_check.exists():
        content = session_check.read_text()
        print("✅ Session已初始化")
        print(f"   {content.strip()}")
        return True
    else:
        print("⚠️ Session未初始化，请运行初始化脚本")
        return False


def check_working_directory():
    """检查工作目录"""
    print("\n📂 工作目录检查:")

    current_dir = Path.cwd()
    print(f"📍 当前目录: {current_dir}")

    # 检查关键项目文件
    key_files = ["main.py", "requirements.txt", "pyproject.toml", "AGENTS.md"]

    for file in key_files:
        if (current_dir / file).exists():
            print(f"✅ 项目文件: {file}")
        else:
            print(f"⚠️ 项目文件缺失: {file}")

    return True


def main():
    """主函数"""
    import sys

    if sys.platform == "win32":
        import codecs

        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

    print("🔍 Devin IDE Session配置检查")
    print("=" * 50)

    # 执行各项检查
    checks = [
        check_working_directory,
        check_project_config,
        check_local_config,
        check_skills,
        check_rules,
        check_session_file,
    ]

    results = []
    for check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 检查失败: {e}")
            results.append(False)

    print("\n" + "=" * 50)

    if all(results):
        print("✅ 所有配置检查通过!")
        print("\n🎉 配置已正确加载，Devin IDE可以正常使用")
        print("\n📝 可用的Skills:")
        print("   /auto-task-execute - 全自动任务执行")
        print("   /auto-task-verify - 全自动任务核验")
        print("   /database-migration - 数据库迁移")
        print("   /fastapi-development - FastAPI开发")
        print("   /gitlab-search - GitLab搜索功能")
        print("   /grill-me - 无状态设计访谈")
        print("   /grill-with-docs - 有状态设计访谈与ADR")
        print("   /python-development - Python开发")
        print("   /tdd - 测试驱动开发")
        print("   /testing-debugging - 测试调试")
        print("\n🔧 可用的MCP服务器:")
        print("   GitLab MCP - GitLab集成")
        print("   Filesystem MCP - 文件系统操作")
        print("   Postgres MCP - 数据库操作")
    else:
        print("⚠️ 部分配置检查失败")
        print("\n📝 建议操作:")
        print("1. 运行初始化脚本: python .devin/scripts/init_devin_config.py")
        print("2. 检查配置文件格式")
        print("3. 确认目录结构正确")
        print("4. 重启Devin IDE")


if __name__ == "__main__":
    main()
