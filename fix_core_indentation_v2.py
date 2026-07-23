#!/usr/bin/env python
"""
批量修复core目录中所有文件的语法错误
移除函数签名中间的TODO docstring
"""

import re
from pathlib import Path


def fix_indentation_errors(file_path):
    """修复单个文件中的缩进错误"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # 例如：
        # def func(
        #     self, param1
        # ):

        pattern = r'(\s+def\s+\w+\s*\([^)]*\n)\s+"""TODO: Add docstring \(Google style\)\."""\s*\n'
        replacement = r"\1"

        content = re.sub(pattern, replacement, content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """主函数"""
    core_dir = Path("core")

    if not core_dir.exists():
        print("core directory not found")
        return

    fixed_count = 0
    total_files = 0

    # 遍历core目录及其子目录中的所有Python文件
    for py_file in core_dir.rglob("*.py"):
        total_files += 1
        if fix_indentation_errors(py_file):
            fixed_count += 1

    print("\nSummary:")
    print(f"Total files processed: {total_files}")
    print(f"Files fixed: {fixed_count}")


if __name__ == "__main__":
    main()
