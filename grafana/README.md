# Grafana provisioning (repository root)

This directory is the **provisioning source for the production/root stacks**:

| Stack | Compose file | Assets used |
|-------|--------------|-------------|
| Root dev stack | `docker-compose.yml` | `grafana/provisioning`, `grafana/dashboards` |
| Production | `deploy/docker-compose.prod.yml` | `grafana/provisioning`, `grafana/dashboards` |
| Monitoring | `deploy/docker-compose.monitoring.yml` | `grafana/provisioning`, `grafana/dashboards` |
| Standalone monitoring | `monitoring/docker-compose.yml` | `monitoring/grafana/*` |

## Layout

- `provisioning/datasources/datasources.yml` — the single datasource file:
  Prometheus (default), VictoriaMetrics, Loki and Tempo. Each datasource declares
  an explicit `uid` (`prometheus`, `victoriametrics`, `loki`, `tempo`) so the
  traces↔logs↔metrics correlation blocks resolve; exactly one datasource is
  `isDefault` to avoid Grafana's "two default datasources" ambiguity.
- `provisioning/dashboards/dashboards.yml` — file provider pointing at
  `/var/lib/grafana/dashboards`, which is mounted from `grafana/dashboards`.
- `dashboards/*.json` — **bare** Grafana dashboard models (top-level `panels`,
  `title`, …). Files wrapped in the HTTP-API envelope `{"dashboard": {...}}`
  are silently ignored by the file provider, so they must not be used here.

## Two stacks, on purpose

`monitoring/` is a self-contained Prometheus + Alertmanager stack with its own
`monitoring/grafana/` assets and Prometheus-only datasources. The repository-root
`grafana/` tree targets the VictoriaMetrics/Loki/Tempo production topology.
They are deliberately separate; do not cross-mount one stack's assets into the
other, and keep datasource uids distinct (`prometheus`/`victoriametrics`/`loki`/`tempo`
here vs the `monitoring/grafana` provisioning there).

## Adding a dashboard

1. Export it from Grafana as a *dashboard model* (not the API wrapper).
2. Drop the JSON in `grafana/dashboards/`.
3. The provider reloads every 10s — no restart needed.
