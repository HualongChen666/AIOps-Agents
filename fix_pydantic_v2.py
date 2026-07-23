import re
from pathlib import Path

api_dir = Path("C:/AIOps_Agent_bak/api")

for py_file in api_dir.glob("*.py"):
    content = py_file.read_text(encoding="utf-8")

    # Pattern to find Config class with schema_extra
    pattern = re.compile(
        r'(\s+)class Config:\s*\n\s+"""TODO: Add docstring \(Google'
        r' style\)\."""\s*\n\s+schema_extra = ({[^}]+})',
        re.MULTILINE,
    )

    def replace_config(match):
        indent = match.group(1)
        schema_extra = match.group(2)
        return f'{indent}model_config = {{"extra": "ignore", "json_schema_extra": {schema_extra}}}'

    new_content = pattern.sub(replace_config, content)

    if new_content != content:
        py_file.write_text(new_content, encoding="utf-8")
        print(f"Fixed: {py_file.name}")

# Also fix schemas directory
schemas_dir = Path("C:/AIOps_Agent_bak/api/schemas")
if schemas_dir.exists():
    for py_file in schemas_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")

        pattern = re.compile(
            r'(\s+)class Config:\s*\n\s+"""TODO: Add docstring \(Google'
            r' style\)\."""\s*\n\s+schema_extra = ({[^}]+})',
            re.MULTILINE,
        )

        def replace_config(match):
            indent = match.group(1)
            schema_extra = match.group(2)
            return (
                f'{indent}model_config = {{"extra": "ignore", "json_schema_extra": {schema_extra}}}'
            )

        new_content = pattern.sub(replace_config, content)

        if new_content != content:
            py_file.write_text(new_content, encoding="utf-8")
            print(f"Fixed: schemas/{py_file.name}")
