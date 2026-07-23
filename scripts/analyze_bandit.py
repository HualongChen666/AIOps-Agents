# flake8: noqa
# isort: skip_file
import re
from collections import defaultdict
from pathlib import Path


def main() -> None:
    report = Path(__file__).parent.parent / "bandit10.txt"
    text = report.read_text(encoding="utf-8")
    pattern = re.compile(
        r"Issue: \[B(\d+):([^\]]+)\].*?Severity: (\w+).*?Location: ([^\n:]+):(\d+):",
        re.DOTALL,
    )
    by_type = defaultdict(int)
    by_file = defaultdict(int)
    by_sev = defaultdict(int)
    details = defaultdict(list)
    for m in pattern.finditer(text):
        b_id, name, sev, file, line = m.groups()
        key = f"B{b_id}:{name}"
        by_type[key] += 1
        by_file[file] += 1
        by_sev[sev] += 1
        details[key].append((file, int(line)))

    print("Severity counts:")
    for sev in sorted(by_sev):
        print(f"  {sev}: {by_sev[sev]}")
    print("\nBy type:")
    for k in sorted(by_type, key=lambda x: by_type[x], reverse=True):
        print(f"  {by_type[k]} {k}")
    print("\nTop files:")
    for f in sorted(by_file, key=lambda x: by_file[x], reverse=True)[:30]:
        print(f"  {by_file[f]} {f}")


if __name__ == "__main__":
    main()
