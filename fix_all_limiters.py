import re
import os
from pathlib import Path

# 需要修复的文件列表
files_to_fix = [
    'api/frontend_advanced_router.py',
    'api/database_monitoring_router.py',
    'api/monitoring_advanced_router.py',
]

def fix_file(filepath):
    """修复单个文件中的@limiter.limit装饰器"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复所有@limiter.limit装饰器后的函数，添加request参数
    pattern = r'(@limiter\.limit\([^)]+\)\s*\n\s*async def \w+\([^)]*\)) ->'

    def add_request_param(match):
        func_def = match.group(1)
        # 检查是否已经有request参数
        if 'request' in func_def.lower():
            return func_def + ' ->'
        # 在参数列表末尾添加request参数
        if ')' in func_def:
            # 在最后一个)之前添加request参数
            func_def = func_def.replace(')', ', request: Request = None)', 1)
        return func_def + ' ->'

    new_content = re.sub(pattern, add_request_param, content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed {filepath}')
    else:
        print(f'No changes needed for {filepath}')

# 修复所有文件
for filepath in files_to_fix:
    if os.path.exists(filepath):
        fix_file(filepath)
    else:
        print(f'File not found: {filepath}')

print('Done!')
