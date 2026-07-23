#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""修复AI引擎代码中的缩进错误"""

import re

file_path = r"C:\AIOps_Agent_bak\core\ai_engine.py"

# 读取文件内容
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 修复重复的try块和缩进错误
# 查找并替换重复的try块
pattern = r"# 费用估算（基于 MODEL_COST, 默认每 1k token 计费）\s+try:\s+# 费用估算（基于 MODEL_COST, 默认每 1k token 计费）\s+try:"  # noqa: E501

replacement = """# 费用估算（基于 MODEL_COST, 默认每 1k token 计费）
    try:"""

content = re.sub(pattern, replacement, content, count=1)

# 修复audit调用为简单的日志记录
audit_pattern = r"from core\.audit_logger import audit\s+audit\([^)]+\)"

audit_replacement = """logger.info(f"LLM call: model={used_model}, tokens={usage.get('total_tokens', 'N/A')}, cost={cost}")  # noqa: E501"""

content = re.sub(audit_pattern, audit_replacement, content, count=1)

# 写回文件
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("AI engine code fix completed")
