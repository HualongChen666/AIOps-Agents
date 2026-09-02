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

    # 移除所有@limiter.limit装饰器
    new_content = re.sub(r'@limiter\.limit\([^)]+\)\s*\n', '', content)

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
