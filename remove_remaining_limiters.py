import re
import os

files_to_fix = [
    'api/test_framework_router.py',
    'api/test_coverage_router.py',
    'api/test_automation_router.py',
]

def fix_file(filepath):
    """移除单个文件中的@limiter.limit装饰器"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除所有@limiter.limit装饰器（包括多行注释）
    new_content = re.sub(r'@limiter\.limit\([^)]+\).*?\n', '', content, flags=re.MULTILINE)

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
