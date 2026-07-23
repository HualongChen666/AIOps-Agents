from coverage import Coverage

cov = Coverage()
cov.load()
data = cov.get_data()
for filename in sorted(data.measured_files()):
    analysis = cov.analysis2(filename)
    fname, stmts, excluded, missing, _ = analysis
    covered = len(stmts) - len(missing)
    total = len(stmts)
    pct = (100.0 * covered / total) if total else 0.0
    if total > 0 and pct < 80:
        print(f"{pct:6.2f}%  {len(missing):>5}/{total:<5} {filename}")
