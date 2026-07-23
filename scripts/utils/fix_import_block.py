# -*- coding: utf-8 -*-
"""Fix ai_feedback_router.py import block"""

from pathlib import Path

file_path = Path("api/ai_feedback_router.py")
content = file_path.read_text(encoding="utf-8")

# Comment out the entire import block
content = content.replace(
    "from core.db_engine import (\n    # insert_feedback,  # Not implemented\n"
    "    # get_feedback_stats,  # Not implemented\n"
    "    # query_recent_feedback,  # Not implemented\n)",
    "# from core.db_engine import (\n#     insert_feedback,  # Not implemented\n"
    "#     get_feedback_stats,  # Not implemented\n"
    "#     query_recent_feedback,  # Not implemented\n# )",
)

file_path.write_text(content, encoding="utf-8")
print("Fixed ai_feedback_router.py import block")
