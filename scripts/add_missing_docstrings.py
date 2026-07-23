# -*- coding: utf-8 -*-
import os
import re

project_root = r"C:\\AIOps_Agent_bak"

audit_patterns = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
audit_entries = []

placeholder = '"""TODO: Add module docstring (Google style)."""\n'


def has_docstring(lines, start_idx):
    """Check if the first non-empty line after start_idx is a docstring."""
    i = start_idx + 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i < len(lines):
        stripped = lines[i].lstrip()
        return stripped.startswith('"""') or stripped.startswith("'''")
    return False


for root, dirs, files in os.walk(project_root):
    for filename in files:
        if not filename.endswith(".py"):
            continue
        path = os.path.join(root, filename)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Skipping file due to read error: {path} - {e}")
            continue
        original_lines = list(lines)
        new_lines = []
        # Detect module docstring insertion point
        insert_module_doc = False
        first_non_comment = 0
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if (
                stripped.startswith("#")
                or stripped == ""
                or stripped.startswith('"""')
                or stripped.startswith("'''")
            ):
                continue
            first_non_comment = i
            break
        else:
            first_non_comment = len(lines)
        if first_non_comment < len(lines):
            if not (
                lines[first_non_comment].lstrip().startswith('"""')
                or lines[first_non_comment].lstrip().startswith("'''")
            ):
                insert_module_doc = True
        else:
            insert_module_doc = True
        if insert_module_doc:
            new_lines.extend(lines[:first_non_comment])
            new_lines.append(placeholder)
            new_lines.extend(lines[first_non_comment:])
            lines = new_lines
            new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Remove audit comments
            if audit_patterns.search(line):
                audit_entries.append(f"{path}:{i+1}: {line.strip()}")
                i += 1
                continue
            # Detect function or class definitions without docstring
            def_match = re.match(r"^(\s*)(def|class)\s+\w+", line)
            if def_match:
                indent = def_match.group(1)
                if not has_docstring(lines, i):
                    new_lines.append(line)
                    new_lines.append(placeholder)
                    i += 1
                    continue
            new_lines.append(line)
            i += 1
        # Write back if any changes
        if new_lines != original_lines:
            try:
                with open(path, "w", encoding="utf-8", errors="ignore") as f:
                    f.writelines(new_lines)
            except Exception as e:
                print(f"Failed to write file {path}: {e}")

# Append audit entries to CHANGELOG
if audit_entries:
    changelog_path = os.path.join(project_root, "CHANGELOG.md")
    try:
        with open(changelog_path, "a", encoding="utf-8") as cl:
            cl.write("\n## Removed audit comments\n")
            for entry in audit_entries:
                cl.write(f"- {entry}\n")
    except Exception as e:
        print(f"Failed to write CHANGELOG: {e}")
