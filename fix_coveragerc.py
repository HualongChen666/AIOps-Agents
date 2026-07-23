#!/usr/bin/env python3
"""Fix .coveragerc: move stray omit entries that were accidentally appended to [run] into the omit option."""
from pathlib import Path

COVERAGERC = Path(".coveragerc")


def parse_coveragerc(path: Path):
    """Parse .coveragerc into sections and detect the omit list and stray entries."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    section = None
    last_option = None
    omit_entries = []
    other_sections = {}
    # We'll collect omit entries from the [run] section
    run_lines = []
    omit_start_idx = None
    omit_end_idx = None
    stray = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
            last_option = None
            continue
        if section == "run":
            # The first option line in run that is not indented starts a new option.
            # Continuation lines are indented.
            if not line.startswith((" ", "\t")) and "=" in line:
                # new option
                key, _, _ = line.partition("=")
                last_option = key.strip()
                if last_option == "omit":
                    omit_start_idx = i
                continue
            if last_option == "omit":
                # continuation line, part of omit list
                if stripped and not stripped.startswith("#"):
                    omit_entries.append(stripped)
                elif not stripped and omit_end_idx is None:
                    omit_end_idx = i
                continue
    # Also find stray block: lines between data_file and [report] that are indented and not part of any known option.
    # Simpler: iterate again and find first non-empty indented lines after the data_file option, before [report].
    # We'll instead scan for all lines that look like file paths and are not in omit yet.
    for line in lines:
        stripped = line.strip()
        if ".py" in stripped and "=" not in stripped and not stripped.startswith("["):
            # likely an omit path line
            p = stripped.strip("\t ")
            if p and p not in omit_entries and not p.startswith(("branch", "parallel", "source", "data_file", "omit")):
                stray.append(p)
    return omit_entries, stray, text


def main():
    if not COVERAGERC.exists():
        raise SystemExit(".coveragerc not found")

    # Read lines and build a clean .coveragerc manually to avoid parser confusion.
    text = COVERAGERC.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Locate sections
    run_start = None
    run_end = None
    sections = {}
    current = None
    section_lines = {}
    for i, line in enumerate(lines):
        if line.strip().startswith("[") and line.strip().endswith("]"):
            if current is not None:
                sections[current] = (section_lines[current], i)
            current = line.strip()[1:-1]
            section_lines[current] = i
    if current is not None:
        sections[current] = (section_lines[current], len(lines))

    # Extract all omit-like entries from run section and the stray block
    run_start, run_end = sections.get("run", (None, None))
    report_start, _ = sections.get("report", (len(lines), len(lines)))
    if run_start is None:
        raise SystemExit("[run] section not found")

    # The omit option starts after "omit =" and continues until the next top-level option (no leading whitespace)
    run_section_lines = lines[run_start:report_start]
    omit_entries = []
    in_omit = False
    for line in run_section_lines:
        s = line.strip()
        if s.startswith("omit") and "=" in s:
            in_omit = True
            continue
        if in_omit:
            # continuation line
            if s and not s.startswith("#"):
                # top-level option ending omit
                if not line.startswith((" ", "\t")) and "=" in s:
                    in_omit = False
                else:
                    omit_entries.append(s)

    # Add stray file path entries from the rest of the run section (indented .py lines without =)
    for line in run_section_lines:
        s = line.strip()
        if ".py" in s and "=" not in s and not s.startswith("[") and s:
            p = s.strip("\t ")
            if p not in omit_entries and not p.startswith(("branch", "parallel", "source", "data_file", "omit")):
                omit_entries.append(p)

    # Deduplicate while preserving order
    seen = set()
    unique_omits = []
    for p in omit_entries:
        key = p.replace("/", "\\").lower()
        if key not in seen:
            seen.add(key)
            unique_omits.append(p)

    # Rebuild [run] section
    new_run_lines = ["[run]", "source = ", "\tcore", "\tapi", "omit = "]
    for p in unique_omits:
        new_run_lines.append(f"\t{p}")
    new_run_lines.extend(["branch = True", "parallel = True", "data_file = .coverage", ""])

    # Replace [run] section lines in the original list with the new run section, then keep the rest starting at [report]
    before_report = lines[report_start:]
    new_lines = new_run_lines + before_report

    COVERAGERC.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"Fixed .coveragerc: {len(unique_omits)} omit entries")


if __name__ == "__main__":
    main()
