#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Remove skip decorators from test files"""

import re

# Read the file
with open("tests/core/test_db_optimization.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove skip decorators
content = re.sub(
    r'    @pytest.mark.skip\(reason="Avoid SQLAlchemy metadata conflicts"\)\n', "", content
)

# Write back
with open("tests/core/test_db_optimization.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Removed skip decorators from test_db_optimization.py")
