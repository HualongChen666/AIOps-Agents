#!/usr/bin/env node
/**
 * Merge every coverage-batched/<dir>/coverage-final.json into one report and
 * evaluate it against the jest.config.js thresholds.
 *
 * Usage: node scripts/merge-coverage.js
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const batchesRoot = path.join(ROOT, 'coverage-batched');
const libCoverage = require('istanbul-lib-coverage');

const map = libCoverage.createCoverageMap({});
let dirs = 0;
for (const entry of fs.readdirSync(batchesRoot)) {
  const f = path.join(batchesRoot, entry, 'coverage-final.json');
  if (fs.existsSync(f)) {
    map.merge(JSON.parse(fs.readFileSync(f, 'utf8')));
    dirs++;
  }
}
const files = map.files();
const keys = ['lines', 'statements', 'functions', 'branches'];
const totals = {};
for (const k of keys) totals[k] = { total: 0, covered: 0 };

const rows = files.map((file) => {
  const s = map.fileCoverageFor(file).toSummary().toJSON();
  for (const k of keys) {
    totals[k].total += s[k].total;
    totals[k].covered += s[k].covered;
  }
  return {
    file: file.replace(ROOT + path.sep, ''),
    lines: s.lines.pct,
    functions: s.functions.pct,
    branches: s.branches.pct,
  };
});

const pct = (k) =>
  totals[k].total === 0 ? 100 : Math.round((totals[k].covered / totals[k].total) * 10000) / 100;

const globalSummary = {};
for (const k of keys) {
  globalSummary[k] = {
    total: totals[k].total,
    covered: totals[k].covered,
    pct: Number(((totals[k].covered / totals[k].total) * 100).toFixed(2)),
  };
}

fs.mkdirSync(path.join(ROOT, 'coverage'), { recursive: true });
fs.writeFileSync(
  path.join(ROOT, 'coverage', 'coverage-summary.json'),
  JSON.stringify({ total: globalSummary }, null, 2)
);

console.log(`merged ${dirs} batch dirs, ${files.length} source files`);
console.log('\n================ MERGED GLOBAL COVERAGE ================');
console.log(
  `lines ${globalSummary.lines.pct}%  statements ${globalSummary.statements.pct}%  functions ${
    globalSummary.functions.pct
  }%  branches ${globalSummary.branches.pct}%`
);

const thresholds = { lines: 96, statements: 95, functions: 95, branches: 89 };
let ok = true;
console.log('\n---- threshold check (jest.config.js) ----');
for (const k of keys ) {
  const pass = globalSummary[k].pct >= thresholds[k];
  ok = ok && pass;
  console.log(
    `  ${k.padEnd(11)} ${String(globalSummary[k].pct).padStart(6)}%  >= ${thresholds[k]}  ${
      pass ? 'PASS' : 'FAIL'
    }`
  );
}
console.log(`\nTHRESHOLDS: ${ok ? 'PASS' : 'FAIL'}`);

rows.sort((a, b) => a.lines - b.lines);
console.log('\n---- per-file (ascending line coverage) ----');
for (const r of rows) {
  console.log(
    `${String(r.lines).padStart(6)}%L ${String(r.functions).padStart(6)}%F ${String(
      r.branches
    ).padStart(6)}%B  ${r.file}`
  );
}
console.log(`\n[merge] total source files: ${rows.length}`);
process.exit(ok ? 0 : 1);
