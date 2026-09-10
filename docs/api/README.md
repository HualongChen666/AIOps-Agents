# API snapshot

`openapi.json` and `openapi.yaml` are **generated artifacts** — both are dumps of
`main.app.openapi()`. Do not edit them by hand.

## Regenerate

```bash
python scripts/generate_openapi_snapshot.py
```

## Verify (CI)

```bash
python scripts/generate_openapi_snapshot.py --check
```

`--check` regenerates the spec in memory and fails when the committed files have
drifted. This runs in `.github/workflows/quality_gates.yml`, so a router change
without a snapshot refresh fails the build instead of silently shipping a stale
spec.

## Current snapshot

- paths: 1,486
- operations: 2,007

Both files are written from the same in-memory document, so their path sets are
identical by construction.
