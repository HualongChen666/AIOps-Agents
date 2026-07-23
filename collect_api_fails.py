import sys
import pytest

args = [
    "tests/api",
    "--no-cov",
    "--disable-warnings",
    "--tb=line",
    "-q",
    "-n", "auto",
    "--timeout=120",
]

code = pytest.main(args, plugins=[])
print(f"pytest exit code: {code}")
