import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def get_mypy_errors(scope=None):
    scope = scope or ["."]
    cmd = [
        sys.executable,
        "-m",
        "mypy",
        "--no-pretty",
        "--show-error-codes",
        "--show-column-numbers",
        "--no-error-summary",
        *scope,
    ]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    return result.stdout + result.stderr, result.returncode


ERROR_RE = re.compile(r"^(.*?\.py):(\d+):(?:(\d+):)?\s*error: (?:.*?) \[(.*?)\]\s*$")


def parse_mypy_errors(text):
    """
    Parse mypy error output and group errors by file.
    
    Args:
        text: Raw mypy error output
        
    Returns:
        Dictionary mapping file paths to sets of (line_number, error_code) tuples
    """
    errors_by_file = {}
    for line in text.splitlines():
        m = ERROR_RE.match(line)
        if m:
            path, lineno, _, code = m.groups()
            path = Path(path)
            if not path.is_absolute():
                path = (ROOT / path).resolve()
            errors_by_file.setdefault(path, set()).add((int(lineno), code))
    return errors_by_file


def add_type_ignore_to_line(line, code):
    """
    Add or update type: ignore comment on a line.
    
    Args:
        line: The original line (without newline)
        code: The error code to ignore
        
    Returns:
        Modified line with type: ignore comment
    """
    # Look for an existing `# type: ignore` comment at the end of the line.
    match = re.search(r"  # type: ignore(?:\[(.*?)\])?$", line)
    if match:
        prefix = line[: match.start()]
        existing = match.group(1)
        if existing is not None:
            codes = [c.strip() for c in existing.split(",") if c.strip()]
            if code not in codes:
                codes.append(code)
        else:
            codes = [code]
        new_line = f"{prefix}  # type: ignore[{','.join(codes)}]"
    else:
        new_line = f"{line}  # type: ignore[{code}]"
    return new_line


def apply_ignores_to_file(path, errors):
    """
    Apply type: ignore comments to a single file.
    
    Args:
        path: Path to the file
        errors: Set of (line_number, error_code) tuples
    """
    if not path.exists():
        return
    
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for lineno, code in errors:
        idx = lineno - 1
        if idx >= len(lines):
            continue
        cur = lines[idx].rstrip("\n")
        new_line = add_type_ignore_to_line(cur, code)
        lines[idx] = new_line + "\n"
    path.write_text("".join(lines), encoding="utf-8")


def apply_ignores(text):
    """
    Apply type: ignore comments to files based on mypy error output.
    
    Args:
        text: Raw mypy error output
    """
    errors_by_file = parse_mypy_errors(text)
    
    for path, errs in errors_by_file.items():
        apply_ignores_to_file(path, errs)


if __name__ == "__main__":
    for i in range(10):
        out, rc = get_mypy_errors()
        if rc == 0:
            print("mypy is now clean")
            break
        count = sum(1 for line in out.splitlines() if "error:" in line)
        print(f"Iteration {i + 1}: {count} errors...")
        apply_ignores(out)
    else:
        out, rc = get_mypy_errors()
        print(out)
        sys.exit(rc)
