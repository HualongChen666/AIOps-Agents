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
    )
    return result.stdout + result.stderr, result.returncode


ERROR_RE = re.compile(r"^(.*?\.py):(\d+):(?:(\d+):)?\s*error: (?:.*?) \[(.*?)\]\s*$")


def apply_ignores(text):
    errors_by_file = {}
    for line in text.splitlines():
        m = ERROR_RE.match(line)
        if m:
            path, lineno, _, code = m.groups()
            path = Path(path)
            if not path.is_absolute():
                path = (ROOT / path).resolve()
            errors_by_file.setdefault(path, set()).add((int(lineno), code))

    for path, errs in errors_by_file.items():
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        for lineno, code in errs:
            idx = lineno - 1
            if idx >= len(lines):
                continue
            cur = lines[idx].rstrip("\n")
            # Look for an existing `# type: ignore` comment at the end of the line.
            match = re.search(r"  # type: ignore(?:\[(.*?)\])?$", cur)
            if match:
                prefix = cur[: match.start()]
                existing = match.group(1)
                if existing is not None:
                    codes = [c.strip() for c in existing.split(",") if c.strip()]
                    if code not in codes:
                        codes.append(code)
                else:
                    codes = [code]
                new_line = f"{prefix}  # type: ignore[{','.join(codes)}]"
            else:
                new_line = f"{cur}  # type: ignore[{code}]"
            lines[idx] = new_line + "\n"
        path.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    for i in range(10):
        out, rc = get_mypy_errors()
        if rc == 0:
            print("mypy is now clean")
            break
        count = sum(1 for l in out.splitlines() if "error:" in l)
        print(f"Iteration {i + 1}: {count} errors...")
        apply_ignores(out)
    else:
        out, rc = get_mypy_errors()
        print(out)
        sys.exit(rc)
