# Benchmarks

## Test coverage

- `core` + `api` + `infrastructure` combined coverage: **~80%**
  (`scripts/run_core_api_infrastructure_tests.py`)
- `tests/api` router tests: **842 passed**, 11 skipped, 2 xfailed
- `tests/core` targeted tests: **3493 passed**, 467 skipped, 0 failed

## Performance

- Phase 4 microservices throughput: **70,000–78,000 ops/sec**
  (target 10,000 ops/sec)
- Prometheus webhook endpoint latency: to be measured with
  `pytest-benchmark` in `tests/e2e`

## E2E

- `tests/e2e/test_prometheus_autoheal.py`: 3/3 passed
- `tests/e2e/test_hardware_remediation_dryrun.py`: 5/5 passed

For reproducible numbers, see `scripts/run_performance_tests.py` and
`docs/performance_baseline.md`.
