#!/usr/bin/env node
/**
 * Memory-safe batched coverage runner.
 *
 * This host has ~1.4 GB RAM and no swap, so a single `jest --coverage` run over
 * the whole suite is OOM-killed (the npm script requests a 4 GB V8 heap while
 * jest workers each reserve ~512 MB; `--runInBand` of the full suite also dies).
 *
 * Because `jest.config.js` sets `collectCoverageFrom` for every components/** and
 * lib/** file, each batched run reports *all* source files (uncovered ones at 0%).
 * Merging the per-batch istanbul `coverage-final.json` therefore yields the exact
 * global coverage a single run would have produced.
 *
 * Usage: node scripts/run-coverage-batched.js
 */
const { execFileSync, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const JEST = path.join(ROOT, 'node_modules', '.bin', 'jest');
const OUT = path.join(ROOT, 'coverage-batched');
const HEAP = process.env.COV_HEAP_MB || '1100';
const CHUNK = Number(process.env.COV_CHUNK || 16);

function listTests() {
  const out = execFileSync('node', [JEST, '--listTests'], { cwd: ROOT, encoding: 'utf8' });
  return out
    .trim()
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
}

function chunk(arr, size) {
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

const tests = listTests();
const batches = chunk(tests, CHUNK);
console.log(`[coverage] ${tests.length} test suites in ${batches.length} batches of <=${CHUNK}\n`);

const batchDirs = [];
batches.forEach((files, idx) => {
  const dir = path.join(OUT, `chunk-${idx}`);
  batchDirs.push(dir);
  console.log(`\n===== batch ${idx + 1}/${batches.length} (${files.length} suites) =====`);
  const res = spawnSync(
    'node',
    [
      `--max-old-space-size=${HEAP}`,
      JEST,
      ...files,
      '--runInBand',
      '--coverage',
      '--coverageReporters=json',
      `--coverageDirectory=${dir}`,
      '--silent',
    ],
    { cwd: ROOT, stdio: 'inherit' }
  );
  console.log(`[coverage] batch ${idx + 1} exited with code ${res.status}`);
});

// ---- merge per-batch coverage maps (istanbul) ----
const libCoverage = require('istanbul-lib-coverage');
const map = libCoverage.createCoverageMap({});
let mergedFiles = 0;
for (const dir of batchDirs) {
  const f = path.join(dir, 'coverage-final.json');
  if (fs.existsSync(f)) {
    map.merge(JSON.parse(fs.readFileSync(f, 'utf8')));
    mergedFiles++;
  }
}
const summary = map.toSummary().toJSON();

// persist merged summary where the project expects it
fs.mkdirSync(path.join(ROOT, 'coverage'), { recursive: true });
fs.writeFileSync(
  path.join(ROOT, 'coverage', 'coverage-summary.json'),
  JSON.stringify(summary, null, 2)
);

const pct = (k) => `${summary[k].pct}%`;
console.log('\n================ MERGED GLOBAL COVERAGE ================');
console.log(`files merged from ${mergedFiles} batches`);
console.log(
  `lines ${pct('lines')}  statements ${pct('statements')}  functions ${pct(
    'functions'
  )}  branches ${pct('branches')}`
);

// thresholds from jest.config.js
const thresholds = { lines: 43, statements: 43, functions: 48, branches: 50 };
console.log('\n---- threshold check (jest.config.js) ----');
let ok = true;
for (const k of Object.keys(thresholds)) {
  const pass = summary[k].pct >= thresholds[k];
  ok = ok && pass;
  console.log(`  ${k.padEnd(11)} ${String(summary[k].pct).padStart(6)}%  >= ${thresholds[k]}  ${pass ? 'PASS' : 'FAIL'}`);
}
console.log(`\nTHRESHOLDS: ${ok ? 'PASS' : 'FAIL'}`);

// per-file report sorted ascending by line coverage
const rows = Object.entries(map.toJSON())
  .map(([file, cov]) => {
    const fc = map.fileCoverageFor(file).toSummary().toJSON();
    return {
      file: file.replace(ROOT + path.sep, ''),
      lines: fc.lines.pct,
      functions: fc.functions.pct,
      branches: fc.branches.pct,
    };
  })
  .sort((a, b) => a.lines - b.lines);

console.log('\n---- per-file (ascending line coverage) ----');
for (const r of rows) {
  console.log(
    `${String(r.lines).padStart(6)}%L ${String(r.functions).padStart(6)}%F ${String(
      r.branches
    ).padStart(6)}%B  ${r.file}`
  );
}
console.log(`\n[coverage] total source files: ${rows.length}`);
process.exit(ok ? 0 : 1);
