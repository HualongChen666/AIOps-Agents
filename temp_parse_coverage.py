import json, sys

def main():
    with open('coverage.json') as f:
        data = json.load(f)
    files = data.get('files', {})
    items = []
    for fname, info in files.items():
        s = info.get('summary', {})
        covered = s.get('covered_lines', 0)
        missing = s.get('missing_lines', 0)
        total = covered + missing
        pct = s.get('percent_covered', 0)
        if total > 0 and pct < 80:
            items.append((pct, missing, total, fname))
    items.sort(key=lambda x: (-x[1], x[0]))
    totals = data.get('totals', {})
    print(f"TOTAL percent_covered: {totals.get('percent_covered', 0):.2f}%")
    for pct, missing, total, fname in items[:80]:
        print(f"{pct:.2f}%  {missing:>5}/{total:<5} {fname}")

if __name__ == '__main__':
    main()
