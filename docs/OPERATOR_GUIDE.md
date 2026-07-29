# Operator Guide

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `HEAL_EXECUTE_ENABLED` | `false` | Allow real software repair command execution. |
| `HEAL_DRY_RUN` | `true` | Force dry-run regardless of `HEAL_EXECUTE_ENABLED`. |
| `HARDWARE_EXECUTE_ENABLED` | `false` | Allow real IPMI/Redfish/RAID/SMART/K8s commands. Keep `false` until reviewed. |
| `AIOPS_ENFORCE_ABAC` | `false` | Enforce attribute-based access control on repair endpoints. |
| `OPENAI_API_KEY` | empty | LLM analysis; empty falls back to rule engine. |
| `ANTHROPIC_API_KEY` | empty | Alternative LLM; optional. |
| `DATABASE_URL` | `postgresql://aiops:aiops@localhost:5432/aiops` | PostgreSQL; empty uses in-memory fallback. |
| `REDIS_URL` | `redis://localhost:6379` | Redis; empty uses in-memory fallback. |

## Approval workflow

1. An alert arrives. The system generates a `runbook` and sets
   `needs_approval=true` for high-risk actions.
2. Operator calls `GET /api/v1/approvals/pending`.
3. Review the `proposal`, `risk_level`, and `commands`.
4. Approve with `PATCH /api/v1/approvals/{alert_id}` or reject it.
5. After approval, `apply_fix` runs commands and `evaluate` reports pass/fail.

## Maintenance windows

`try_auto_heal` checks the alert timestamp against configured maintenance windows
before executing. Outside windows, it returns `pending_approval`.

## Safety checklist

- [ ] `HARDWARE_EXECUTE_ENABLED` is `false` in production until runbooks are audited.
- [ ] `HEAL_EXECUTE_ENABLED` is `false` for destructive commands.
- [ ] `AIOPS_ENFORCE_ABAC` is `true` in multi-tenant deployments.
