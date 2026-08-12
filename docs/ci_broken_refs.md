# CI Broken References Scan Report

## Summary

- Scan scope: `.github/workflows/*.yml` (13 files)
- Scan time: 2026-08-12T06:00:07.703104+00:00
- `yaml.safe_load` pass rate: 13/13
- Missing path references (current): 0
- `3.14` Python version references (current): 0
- `yamllint` exit code: 1
- `yamllint` total: 191 errors, 29 warnings

## Confirmed Historical Broken References (Fixed)

| File | Line | Broken Reference | Issue | Status |
|------|------|------------------|-------|--------|
| test.yml | 18 | `python-version: ['3.11', '3.12', '3.14']` | Invalid Python version (3.14) | Removed 3.14 |
| ci.yml | 264 | `tests/performance/` | Missing directory | Replaced/removed step |
| ci.yml | 310 | `tests/security/` | Missing directory | Replaced/removed step |
| ci.yml | 215 | `tests/test_integration_*.py` | Missing test files | Replaced with tests/core tests/api |
| build.yml | 86 | `helm/aiops-agent/values-prod.yaml` | Missing Helm values | Created |
| build.yml | 127 | `helm/aiops-agent/values-staging.yaml` | Missing Helm values | Created |

## Current Scan Results

### Missing Path References

No missing path references detected.

### Python 3.14 References

No `3.14` references detected.

### `yaml.safe_load` Parse Errors

All workflow YAML files parse successfully.

## yamllint Validation

Command: `python -m yamllint .github/workflows/`

- Exit code: `1`
- Errors: `191`
- Warnings: `29`

### Per-file Counts

| File | errors | warnings |
|------|--------|----------|
| .github/workflows/addons.yml | 4 | 2 |
| .github/workflows/build.yml | 17 | 2 |
| .github/workflows/ci-cd.yml | 42 | 2 |
| .github/workflows/ci.yml | 14 | 2 |
| .github/workflows/ci_p1.yml | 5 | 2 |
| .github/workflows/coverage.yml | 10 | 2 |
| .github/workflows/coverage_check.yml | 16 | 2 |
| .github/workflows/integration-test-automation.yml | 5 | 4 |
| .github/workflows/quality_gates.yml | 9 | 2 |
| .github/workflows/quick-tests.yml | 12 | 2 |
| .github/workflows/release.yml | 3 | 2 |
| .github/workflows/test-collection-validation.yml | 36 | 2 |
| .github/workflows/test.yml | 18 | 3 |

### Per-rule Counts

| Rule | Count |
|------|-------|
| trailing-spaces | 95 |
| line-length | 40 |
| brackets | 34 |
| document-start | 13 |
| new-lines | 13 |
| truthy | 13 |
| key-duplicates | 9 |
| comments | 3 |

### Raw yamllint Output

<details>
<summary>Expand full output</summary>

```
.github/workflows/addons.yml
  1:1       warning  missing document start "---"  (document-start)
  1:21      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  28:1      error    trailing spaces  (trailing-spaces)
  51:1      error    trailing spaces  (trailing-spaces)
  53:81     error    line too long (88 > 80 characters)  (line-length)

.github/workflows/build.yml
  1:1       warning  missing document start "---"  (document-start)
  1:23      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  5:16      error    too many spaces inside brackets  (brackets)
  5:21      error    too many spaces inside brackets  (brackets)
  29:1      error    trailing spaces  (trailing-spaces)
  53:1      error    trailing spaces  (trailing-spaces)
  55:9      error    duplication of key "name" in mapping  (key-duplicates)
  56:5      error    duplication of key "runs-on" in mapping  (key-duplicates)
  60:5      error    duplication of key "steps" in mapping  (key-duplicates)
  78:1      error    trailing spaces  (trailing-spaces)
  89:1      error    trailing spaces  (trailing-spaces)
  94:1      error    trailing spaces  (trailing-spaces)
  96:9      error    duplication of key "name" in mapping  (key-duplicates)
  97:5      error    duplication of key "runs-on" in mapping  (key-duplicates)
  98:5      error    duplication of key "needs" in mapping  (key-duplicates)
  99:5      error    duplication of key "if" in mapping  (key-duplicates)
  101:5     error    duplication of key "steps" in mapping  (key-duplicates)
  119:1     error    trailing spaces  (trailing-spaces)

.github/workflows/ci-cd.yml
  1:1       warning  missing document start "---"  (document-start)
  1:24      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  5:16      error    too many spaces inside brackets  (brackets)
  5:30      error    too many spaces inside brackets  (brackets)
  7:16      error    too many spaces inside brackets  (brackets)
  7:30      error    too many spaces inside brackets  (brackets)
  32:1      error    trailing spaces  (trailing-spaces)
  39:1      error    trailing spaces  (trailing-spaces)
  43:81     error    line too long (85 > 80 characters)  (line-length)
  45:1      error    trailing spaces  (trailing-spaces)
  56:1      error    trailing spaces  (trailing-spaces)
  60:81     error    line too long (97 > 80 characters)  (line-length)
  69:1      error    trailing spaces  (trailing-spaces)
  79:81     error    line too long (117 > 80 characters)  (line-length)
  80:1      error    trailing spaces  (trailing-spaces)
  83:81     error    line too long (81 > 80 characters)  (line-length)
  84:1      error    trailing spaces  (trailing-spaces)
  108:1     error    trailing spaces  (trailing-spaces)
  114:1     error    trailing spaces  (trailing-spaces)
  118:81    error    line too long (84 > 80 characters)  (line-length)
  120:1     error    trailing spaces  (trailing-spaces)
  126:81    error    line too long (93 > 80 characters)  (line-length)
  127:1     error    trailing spaces  (trailing-spaces)
  133:1     error    trailing spaces  (trailing-spaces)
  136:1     error    trailing spaces  (trailing-spaces)
  149:1     error    trailing spaces  (trailing-spaces)
  154:1     error    trailing spaces  (trailing-spaces)
  159:1     error    trailing spaces  (trailing-spaces)
  167:1     error    trailing spaces  (trailing-spaces)
  170:1     error    trailing spaces  (trailing-spaces)
  186:1     error    trailing spaces  (trailing-spaces)
  192:1     error    trailing spaces  (trailing-spaces)
  196:81    error    line too long (85 > 80 characters)  (line-length)
  198:1     error    trailing spaces  (trailing-spaces)
  209:1     error    trailing spaces  (trailing-spaces)
  213:81    error    line too long (97 > 80 characters)  (line-length)
  222:1     error    trailing spaces  (trailing-spaces)
  241:1     error    trailing spaces  (trailing-spaces)
  245:1     error    trailing spaces  (trailing-spaces)
  258:1     error    trailing spaces  (trailing-spaces)
  262:1     error    trailing spaces  (trailing-spaces)
  266:1     error    trailing spaces  (trailing-spaces)
  293:1     error    trailing spaces  (trailing-spaces)

.github/workflows/ci.yml
  1:1       warning  missing document start "---"  (document-start)
  1:21      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  37:81     error    line too long (84 > 80 characters)  (line-length)
  42:81     error    line too long (82 > 80 characters)  (line-length)
  43:81     error    line too long (98 > 80 characters)  (line-length)
  117:81    error    line too long (93 > 80 characters)  (line-length)
  124:81    error    line too long (93 > 80 characters)  (line-length)
  126:81    error    line too long (163 > 80 characters)  (line-length)
  148:81    error    line too long (148 > 80 characters)  (line-length)
  208:81    error    line too long (87 > 80 characters)  (line-length)
  256:81    error    line too long (87 > 80 characters)  (line-length)
  303:81    error    line too long (87 > 80 characters)  (line-length)
  331:81    error    line too long (85 > 80 characters)  (line-length)
  332:81    error    line too long (83 > 80 characters)  (line-length)
  365:81    error    line too long (99 > 80 characters)  (line-length)

.github/workflows/ci_p1.yml
  1:1       warning  missing document start "---"  (document-start)
  1:33      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  5:16      error    too many spaces inside brackets  (brackets)
  5:30      error    too many spaces inside brackets  (brackets)
  7:16      error    too many spaces inside brackets  (brackets)
  7:30      error    too many spaces inside brackets  (brackets)

.github/workflows/coverage.yml
  1:1       warning  missing document start "---"  (document-start)
  1:28      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  5:16      error    too many spaces inside brackets  (brackets)
  5:30      error    too many spaces inside brackets  (brackets)
  7:16      error    too many spaces inside brackets  (brackets)
  7:30      error    too many spaces inside brackets  (brackets)
  28:1      error    trailing spaces  (trailing-spaces)
  31:81     error    line too long (142 > 80 characters)  (line-length)
  32:1      error    trailing spaces  (trailing-spaces)
  37:1      error    trailing spaces  (trailing-spaces)
  53:1      error    trailing spaces  (trailing-spaces)

.github/workflows/coverage_check.yml
  1:1       warning  missing document start "---"  (document-start)
  1:21      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  5:16      error    too many spaces inside brackets  (brackets)
  5:30      error    too many spaces inside brackets  (brackets)
  7:16      error    too many spaces inside brackets  (brackets)
  7:30      error    too many spaces inside brackets  (brackets)
  32:1      error    trailing spaces  (trailing-spaces)
  35:81     error    line too long (138 > 80 characters)  (line-length)
  36:1      error    trailing spaces  (trailing-spaces)
  44:81     error    line too long (89 > 80 characters)  (line-length)
  47:1      error    trailing spaces  (trailing-spaces)
  53:1      error    trailing spaces  (trailing-spaces)
  60:1      error    trailing spaces  (trailing-spaces)
  68:81     error    line too long (86 > 80 characters)  (line-length)
  70:81     error    line too long (86 > 80 characters)  (line-length)
  72:1      error    trailing spaces  (trailing-spaces)
  89:1      error    trailing spaces  (trailing-spaces)

.github/workflows/integration-test-automation.yml
  1:1       warning  missing document start "---"  (document-start)
  1:34      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  5:16      error    too many spaces inside brackets  (brackets)
  5:30      error    too many spaces inside brackets  (brackets)
  7:16      error    too many spaces inside brackets  (brackets)
  7:30      error    too many spaces inside brackets  (brackets)
  9:25      warning  too few spaces before comment: expected 2  (comments)
  10:22     warning  too few spaces before comment: expected 2  (comments)

.github/workflows/quality_gates.yml
  1:1       warning  missing document start "---"  (document-start)
  1:20      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  29:1      error    trailing spaces  (trailing-spaces)
  33:1      error    trailing spaces  (trailing-spaces)
  37:1      error    trailing spaces  (trailing-spaces)
  41:1      error    trailing spaces  (trailing-spaces)
  45:1      error    trailing spaces  (trailing-spaces)
  49:1      error    trailing spaces  (trailing-spaces)
  52:81     error    line too long (86 > 80 characters)  (line-length)
  53:1      error    trailing spaces  (trailing-spaces)

.github/workflows/quick-tests.yml
  1:1       warning  missing document start "---"  (document-start)
  1:18      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  5:16      error    too many spaces inside brackets  (brackets)
  5:30      error    too many spaces inside brackets  (brackets)
  7:16      error    too many spaces inside brackets  (brackets)
  7:30      error    too many spaces inside brackets  (brackets)
  26:1      error    trailing spaces  (trailing-spaces)
  29:81     error    line too long (100 > 80 characters)  (line-length)
  30:1      error    trailing spaces  (trailing-spaces)
  33:1      error    trailing spaces  (trailing-spaces)
  47:1      error    trailing spaces  (trailing-spaces)
  50:81     error    line too long (120 > 80 characters)  (line-length)
  51:1      error    trailing spaces  (trailing-spaces)

.github/workflows/release.yml
  1:1       warning  missing document start "---"  (document-start)
  1:21      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  41:1      error    trailing spaces  (trailing-spaces)
  61:1      error    trailing spaces  (trailing-spaces)

.github/workflows/test-collection-validation.yml
  1:1       warning  missing document start "---"  (document-start)
  1:33      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  5:16      error    too many spaces inside brackets  (brackets)
  5:30      error    too many spaces inside brackets  (brackets)
  7:16      error    too many spaces inside brackets  (brackets)
  7:30      error    too many spaces inside brackets  (brackets)
  30:1      error    trailing spaces  (trailing-spaces)
  36:1      error    trailing spaces  (trailing-spaces)
  40:81     error    line too long (92 > 80 characters)  (line-length)
  42:1      error    trailing spaces  (trailing-spaces)
  46:81     error    line too long (85 > 80 characters)  (line-length)
  48:1      error    trailing spaces  (trailing-spaces)
  59:1      error    trailing spaces  (trailing-spaces)
  63:81     error    line too long (88 > 80 characters)  (line-length)
  64:81     error    line too long (81 > 80 characters)  (line-length)
  65:81     error    line too long (99 > 80 characters)  (line-length)
  66:1      error    trailing spaces  (trailing-spaces)
  70:81     error    line too long (97 > 80 characters)  (line-length)
  79:1      error    trailing spaces  (trailing-spaces)
  100:81    error    line too long (104 > 80 characters)  (line-length)
  101:1     error    trailing spaces  (trailing-spaces)
  129:1     error    trailing spaces  (trailing-spaces)
  135:1     error    trailing spaces  (trailing-spaces)
  139:81    error    line too long (93 > 80 characters)  (line-length)
  140:1     error    trailing spaces  (trailing-spaces)
  175:1     error    trailing spaces  (trailing-spaces)
  181:1     error    trailing spaces  (trailing-spaces)
  189:1     error    trailing spaces  (trailing-spaces)
  191:1     error    trailing spaces  (trailing-spaces)
  198:1     error    trailing spaces  (trailing-spaces)
  201:1     error    trailing spaces  (trailing-spaces)
  210:1     error    trailing spaces  (trailing-spaces)
  214:1     error    trailing spaces  (trailing-spaces)
  219:1     error    trailing spaces  (trailing-spaces)
  224:1     error    trailing spaces  (trailing-spaces)
  230:1     error    trailing spaces  (trailing-spaces)
  235:81    error    line too long (86 > 80 characters)  (line-length)

.github/workflows/test.yml
  1:1       warning  missing document start "---"  (document-start)
  1:33      error    wrong new line character: expected \n  (new-lines)
  3:1       warning  truthy value should be one of [false, true]  (truthy)
  5:16      error    too many spaces inside brackets  (brackets)
  5:30      error    too many spaces inside brackets  (brackets)
  7:16      error    too many spaces inside brackets  (brackets)
  7:30      error    too many spaces inside brackets  (brackets)
  9:25      warning  too few spaces before comment: expected 2  (comments)
  36:1      error    trailing spaces  (trailing-spaces)
  42:1      error    trailing spaces  (trailing-spaces)
  46:1      error    trailing spaces  (trailing-spaces)
  59:1      error    trailing spaces  (trailing-spaces)
  81:1      error    trailing spaces  (trailing-spaces)
  88:3      error    duplication of key "retention-days" in mapping  (key-duplicates)
  106:1     error    trailing spaces  (trailing-spaces)
  112:1     error    trailing spaces  (trailing-spaces)
  116:81    error    line too long (84 > 80 characters)  (line-length)
  118:1     error    trailing spaces  (trailing-spaces)
  124:1     error    trailing spaces  (trailing-spaces)
  130:1     error    trailing spaces  (trailing-spaces)
  142:1     error    trailing spaces  (trailing-spaces)


```
</details>

## Conclusion

All path/version reference errors have been addressed and `yaml.safe_load` passes for every workflow. `yamllint` still reports style and structural issues (new-lines, trailing-spaces, line-length, truthy, key-duplicates, brackets, etc.) that should be cleaned up in the next 1.1.2-1.1.5 steps.
