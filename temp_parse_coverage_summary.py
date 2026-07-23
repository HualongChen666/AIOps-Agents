import json

def main(path='coverage_summary.json', top=80, threshold=80):
    with open(path) as f:
        data = json.load(f)
    files = data.get('files', {})
    items = []
    for fname, info in files.items():
        s = info.get('summary', {})
        missing = s.get('missing_lines', 0)
        covered = s.get('covered_lines', 0)
        total = missing + covered
        pct = s.get('percent_covered', 0)
        if total > 0 and pct < threshold:
            items.append((pct, missing, total, fname))
    items.sort(key=lambda x: (-x[1], x[0]))
    for pct, missing, total, fname in items[:top]:
        print(f"{pct:.2f}%  {missing:>5}/{total:<5} {fname}")

if __name__ == '__main__':
    main()
