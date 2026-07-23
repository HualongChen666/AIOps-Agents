# -*- coding: utf-8 -*-
import io
import os
import sys

# Set UTF-8 encoding for all I/O operations
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")

# Set default encoding for file operations
os.environ["PYTHONIOENCODING"] = "utf-8"
