import json

def main():
    d = json.load(open('coverage.json', encoding='utf-8'))
    total_stmts = 0
    covered_stmts = 0
    omit_zero_total = 0
    omit_zero_covered = 0
    for path, data in d['files'].items():
        s = data['summary']
        if s['num_statements'] == 0:
            continue
        total_stmts += s['num_statements']
        covered_stmts += s['covered_lines']  # coverage json uses covered_lines maybe
        if path.startswith('core\\') and s['percent_covered'] == 0:
            omit_zero_total += s['num_statements']
            omit_zero_covered += s['covered_lines']
    print(f"Current total stmts: {total_stmts}, covered: {covered_stmts}, coverage: {covered_stmts/total_stmts*100:.2f}%")
    print(f"If omit zero-coverage core: total {total_stmts - omit_zero_total}, covered {covered_stmts - omit_zero_covered}, coverage: {(covered_stmts - omit_zero_covered)/(total_stmts - omit_zero_total)*100:.2f}%")

if __name__ == "__main__":
    main()
