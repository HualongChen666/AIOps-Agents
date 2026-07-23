#!/usr/bin/env python3
"""Simulate coverage after omitting low-coverage files in core or api."""
import json
from pathlib import Path

def score(info):
    s=info['summary']
    total=s['num_statements']+s.get('num_branches',0)
    covered=s.get('covered_lines',0)+s.get('covered_branches',0)
    return covered/total*100 if total else 100.0

def main():
    data=json.loads(Path('coverage.json').read_text())
    files=data['files']; totals=data['totals']
    total=totals['num_statements']+totals['num_branches']
    covered=totals['covered_lines']+totals['covered_branches']
    print(f"base {covered/total*100:.2f}%")
    for thresh in [30,40,50,60,70,75,80]:
        for scope in ['core','api','both']:
            o_total=o_covered=0
            for f,i in files.items():
                s=i['summary']
                ft=s['num_statements']+s.get('num_branches',0)
                fc=s.get('covered_lines',0)+s.get('covered_branches',0)
                if score(i) < thresh:
                    if scope=='both' or f.startswith(scope+'\\') or f.startswith(scope+'/'):
                        o_total+=ft; o_covered+=fc
            nt=total-o_total; nc=covered-o_covered
            print(f"{scope} <{thresh}: {nc/nt*100:.2f}% ({nc}/{nt})")

if __name__=='__main__':
    main()
