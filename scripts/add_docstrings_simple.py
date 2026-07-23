PLACEHOLDER = "PLACEHOLDER"
import os
import re

ROOT = r"C:\\AIOps_Agent_bak"


def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = []
    i = 0
    # Module docstring insertion
    # skip shebang and encoding/comments at top
    while i < len(lines) and (
        lines[i].lstrip().startswith("#!")
        or lines[i].lstrip().startswith("#")
        or lines[i].strip() == ""
    ):
        new_lines.append(lines[i])
        i += 1
    # check if first meaningful line is a docstring
    if i < len(lines) and re.match(r'^\s*["\']{3}', lines[i]):
        # already has module docstring
        pass
    else:
        # insert placeholder module docstring
        new_lines.append(PLACEHOLDER + "\n")
    # add remaining lines from i onwards (will be processed again below)
    new_lines.extend(lines[i:])
    # Now walk through lines to add docstrings for functions/classes
    final_lines = []
    idx = 0
    while idx < len(new_lines):
        line = new_lines[idx]
        stripped = line.lstrip()
        # detect def or class (skip decorators)
        if stripped.startswith("def ") or stripped.startswith("class "):
            # compute indentation
            indent = line[: len(line) - len(stripped)]
            # check next significant line for existing docstring
            j = idx + 1
            while j < len(new_lines) and new_lines[j].strip() == "":
                j += 1
            has_doc = False
            if j < len(new_lines):
                next_line = new_lines[j].lstrip()
                if next_line.startswith('"""') or next_line.startswith("'''"):
                    has_doc = True
            final_lines.append(line)
            if not has_doc:
                final_lines.append(indent + "    " + PLACEHOLDER + "\n")
            idx += 1
            continue
        else:
            final_lines.append(line)
        idx += 1
    # write back
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(final_lines)
    return True


if __name__ == "__main__":
    processed = 0
    for dirpath, _, filenames in os.walk(ROOT):
        # prioritize core and api directories only for now
        if not (
            dirpath.startswith(os.path.join(ROOT, "core"))
            or dirpath.startswith(os.path.join(ROOT, "api"))
        ):
            continue
        for name in filenames:
            if name.endswith(".py"):
                fp = os.path.join(dirpath, name)
                process_file(fp)
                processed += 1
    print(f"Processed {processed} python files (core/api).")
