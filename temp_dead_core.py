import json
import os
import re
from pathlib import Path

def main():
    cov = json.load(open('coverage.json', encoding='utf-8'))
    zero_core = []
    for path, data in cov['files'].items():
        if not (path.startswith('core/') or path.startswith('core\\')):
            continue
        if data['summary']['num_statements'] == 0:
            continue
        if data['summary']['percent_covered'] == 0:
            zero_core.append(path)
    print(f"Zero-coverage core files: {len(zero_core)}")
    for p in sorted(zero_core):
        print(p)

if __name__ == "__main__":
    main()
