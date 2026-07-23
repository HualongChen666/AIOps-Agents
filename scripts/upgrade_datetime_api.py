#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Batch upgrade script for datetime.utcnow() to datetime.now(timezone.utc)
"""

import re
from pathlib import Path


def upgrade_datetime_utcnow(file_path):
    """升级单个文件中的datetime.utcnow()"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 1. 检查是否已经导入了timezone
        if "from datetime import" in content and "timezone" not in content:
            # 在datetime导入中添加timezone
            content = re.sub(
                r"from datetime import ([^\\n]+)",
                lambda m: (
                    f"from datetime import {m.group(1).rstrip()}, timezone"
                    if "timezone" not in m.group(1)
                    else m.group(0)
                ),
                content,
            )

        # 2. 替换 datetime.utcnow() 为 datetime.now(timezone.utc)
        content = re.sub(r"datetime\.utcnow\(\)", "datetime.now(timezone.utc)", content)

        # 3. 替换 field(default_factory=datetime.utcnow) 为  # noqa: E501
        # field(default_factory=lambda: datetime.now(timezone.utc))
        content = re.sub(
            r"field\(default_factory=datetime\.utcnow\)",
            "field(default_factory=lambda: datetime.now(timezone.utc))",
            content,
        )

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return False


def main():
    """主函数"""
    # 搜索所有包含datetime.utcnow的Python文件
    core_dir = Path("C:/AIOps_Agent_bak/core")

    if not core_dir.exists():
        print(f"Directory does not exist: {core_dir}")
        return

    # 查找所有Python文件
    python_files = []
    for py_file in core_dir.rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                if "datetime.utcnow" in content:
                    python_files.append(py_file)
        except Exception as e:
            print(f"Error reading file {py_file}: {e}")

    print(f"Found {len(python_files)} files to upgrade")

    # 批量升级
    upgraded_count = 0
    for file_path in python_files:
        if upgrade_datetime_utcnow(file_path):
            print(f"Upgraded: {file_path}")
            upgraded_count += 1

    print(f"Total upgraded: {upgraded_count} files")


if __name__ == "__main__":
    main()
