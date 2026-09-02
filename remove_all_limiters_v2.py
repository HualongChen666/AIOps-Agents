import re

# 读取文件
with open('api/alerts_advanced_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 移除所有@limiter.limit装饰器（包括多行注释）
content = re.sub(r'@limiter\.limit\([^)]+\).*?\n', '', content, flags=re.MULTILINE)

# 写回文件
with open('api/alerts_advanced_router.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Removed all @limiter.limit decorators from alerts_advanced_router.py')
