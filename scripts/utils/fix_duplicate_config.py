# -*- coding: utf-8 -*-
"""
Fix Duplicate Configuration Script
修复重复配置脚本

用于检测和修复.env文件中的重复配置项
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple


def find_duplicate_configs(env_file: Path) -> List[Tuple[str, List[int]]]:
    """查找重复的配置项"""

    if not env_file.exists():
        print(f"[ERROR] {env_file} not found")  # noqa: F541
        return []

    print(f"[INFO] Reading {env_file}...")  # noqa: F541

    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 跟踪配置项
    config_map: Dict[str, List[int]] = {}

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=")[0].strip()
            if key not in config_map:
                config_map[key] = []
            config_map[key].append(idx + 1)  # 1-based line number

    # 找出重复项
    duplicates = [(key, line_nums) for key, line_nums in config_map.items() if len(line_nums) > 1]

    return duplicates


def fix_duplicate_configs(env_file: Path, keep_first: bool = True) -> bool:
    """修复重复的配置项"""

    duplicates = find_duplicate_configs(env_file)

    if not duplicates:
        print("[INFO] No duplicate configurations found")
        return True

    print(f"\n[WARN] Found {len(duplicates)} duplicate configuration(s):")  # noqa: F541
    for key, line_nums in duplicates:
        print(f"  - {key}: lines {line_nums}")  # noqa: F541

    # 读取文件
    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 修复重复项
    new_lines = []
    seen_keys = set()

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=")[0].strip()

            if key in seen_keys:
                # 跳过重复项
                print(f"[FIX] Removing duplicate '{key}' at line {idx + 1}")  # noqa: F541
                continue
            else:
                seen_keys.add(key)
                new_lines.append(line)
        else:
            new_lines.append(line)

    # 备份原文件
    backup_file = env_file.with_suffix(env_file.suffix + ".backup")
    print(f"[INFO] Backing up to {backup_file}")  # noqa: F541
    os.replace(env_file, backup_file)

    # 写入修复后的文件
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"[SUCCESS] Fixed duplicate configurations in {env_file}")  # noqa: F541
    return True


def check_config_consistency(env_file: Path) -> bool:
    """检查配置一致性"""

    print(f"\n=== Configuration Consistency Check ===\n")  # noqa: F541

    if not env_file.exists():
        print(f"[ERROR] {env_file} not found")  # noqa: F541
        return False

    # 读取文件
    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 检查空值
    empty_configs = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            parts = stripped.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if not value or value == '""' or value == "''":
                    empty_configs.append((key, idx + 1))

    if empty_configs:
        print(f"[WARN] Found {len(empty_configs)} empty configuration(s):")  # noqa: F541
        for key, line_num in empty_configs:
            print(f"  - {key}: line {line_num}")  # noqa: F541
    else:
        print("[INFO] No empty configurations found")

    # 检查注释
    commented_configs = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=")[0].strip().lstrip("#")
            commented_configs.append((key, idx + 1))

    if commented_configs:
        print(f"[INFO] Found {len(commented_configs)} commented configuration(s):")  # noqa: F541
        for key, line_num in commented_configs:
            print(f"  - {key}: line {line_num}")  # noqa: F541

    return True


def main():
    """主函数"""

    print("\n=== Fix Duplicate Configuration ===\n")

    # 检查.env文件
    env_file = Path(".env")
    if not env_file.exists():
        print("[ERROR] .env file not found")
        print("[HINT] Run 'python setup_production.py' first")
        return

    # 检查重复配置
    duplicates = find_duplicate_configs(env_file)

    if duplicates:
        print(f"\n[WARN] Found {len(duplicates)} duplicate configuration(s):")  # noqa: F541
        for key, line_nums in duplicates:
            print(f"  - {key}: lines {line_nums}")  # noqa: F541

        # 询问是否修复
        print("\n[INFO] Fixing duplicate configurations (keeping first occurrence)...")
        if fix_duplicate_configs(env_file, keep_first=True):
            print("[SUCCESS] Duplicate configurations fixed")
    else:
        print("[INFO] No duplicate configurations found")

    # 检查配置一致性
    check_config_consistency(env_file)

    print("\n=== Check Complete ===\n")


if __name__ == "__main__":
    main()
