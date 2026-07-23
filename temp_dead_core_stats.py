import json

def main():
    d = json.load(open('coverage.json', encoding='utf-8'))
    zero_core = []
    total = 0
    for k, v in d['files'].items():
        if not (k.startswith('core/') or k.startswith('core\\')):
            continue
        s = v['summary']
        if s['num_statements'] == 0:
            continue
        if s['percent_covered'] == 0:
            zero_core.append(k)
            total += s['num_statements']
    print(f"Zero-coverage core files: {len(zero_core)}, statements: {total}")
    for p in sorted(zero_core):
        print(p)

if __name__ == "__main__":
    main()
