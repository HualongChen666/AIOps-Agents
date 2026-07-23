# -*- coding: utf-8 -*-
"""Fix ai_feedback_router.py"""

from pathlib import Path

file_path = Path("api/ai_feedback_router.py")
content = file_path.read_text(encoding="utf-8")

# Comment out the closing parenthesis on line 155
content = content.replace(
    "            # user_agent    = user_agent,\n        )",
    "            # user_agent    = user_agent,\n        # )",
)

file_path.write_text(content, encoding="utf-8")
print("Fixed ai_feedback_router.py")
