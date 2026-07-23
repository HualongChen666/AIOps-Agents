import json
import sys

def main(prefix=None):
    d = json.load(open('coverage.json', encoding='utf-8'))
    files = []
    for k, v in d['files'].items():
        s = v['summary']
        if s['num_statements'] == 0:
            continue
        if prefix and not k.startswith(prefix):
            continue
        miss = int(s.get('missing_lines', 0))
        files.append((k, miss, s['num_statements'], s['percent_covered']))
    files.sort(key=lambda x: -x[1])
    print(f"{'file':60} {'miss':>6} {'total':>6} {'cover':>7}")
    for f in files:
        print(f"{f[0]:60} {f[1]:6} {f[2]:6} {f[3]:6.1f}%")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
