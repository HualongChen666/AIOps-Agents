import re

# 读取文件
with open('api/alerts_advanced_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复所有@limiter.limit装饰器后的函数，添加request参数
# 模式：在async def后面添加request: Request = None参数
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

content = re.sub(pattern, add_request_param, content)

# 写回文件
with open('api/alerts_advanced_router.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed alerts_advanced_router.py')
