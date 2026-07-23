import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else 'coverage.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

totals = data.get('totals', {})
print('totals:', totals)
files = data.get('files', {})
items = []
for fname, info in files.items():
    s = info.get('summary', {})
    missing = s.get('missing_lines', 0)
    covered = s.get('covered_lines', 0)
    total = missing + covered
    pct = s.get('percent_covered', 0)
    if total > 0 and pct < 80:
        items.append((pct, missing, total, fname))
items.sort(key=lambda x: (-x[1], -x[0]))
print('num low files:', len(items))
for pct, missing, total, fname in items[:100]:
    print(f"{pct:.2f}%  {missing:>6}/{total:<6} {fname}")
