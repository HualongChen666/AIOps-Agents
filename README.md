# aiops-agent

![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?style=flat-square)
![Docker Compose](https://img.shields.io/badge/docker--compose-ready-2496ED.svg?style=flat-square)
![Coverage](coverage.svg)

> **Self-hosted AI SRE that turns Prometheus alerts into approved, verified, auditable repairs for software and hardware incidents.**

`aiops-agent` is an open-source SRE agent for Prometheus users. It consumes
Alertmanager notifications, normalizes them into a uniform alert model, and runs
a deterministic repair workflow that selects runbooks, generates dry-run
commands, and only executes after approval.

Hardware remediation (IPMI, Redfish, RAID, SMART, Kubernetes drain) stays in
dry-run by default, while software repairs can be promoted to auto-execution once
your team is confident.

---

## Start in 60 seconds

```bash
git clone https://github.com/aiops-team/aiops-agent.git
cd aiops-agent
cp .env.example .env
docker compose up
```

Open `http://localhost:8000/docs` and try the Prometheus webhook:

```bash
curl -X POST http://localhost:8000/api/v1/alerts/prometheus \
  -H "Content-Type: application/json" \
  -d @examples/curl/createAnomaly.sh
```

---

## 5-minute demo

See [docs/QUICKSTART.md](docs/QUICKSTART.md#demo) for an asciinema walkthrough
that shows a Prometheus alert flowing through normalization, runbook selection,
approval, and dry-run repair.

---

## Core vs Add-ons

The 60-second quickstart above starts the **core** product: alert ingest,
normalization, approval, audit, auto-heal, repair, and health endpoints.
Optional **add-on packs** provide AI/ML, observability/topology, SRE workflows,
multi-cloud integrations, security, IaC, and plugins.

Add-ons are disabled by default. Enable a pack by setting `ENABLE_ADDONS=true`
and the matching pack flag:

```text
ENABLE_ADDONS=true
RAG_ENABLED=true
LLM_ROUTER_ENABLED=true
```

Or start the AI Plus pack with Docker Compose profiles:

```bash
docker compose -f docker-compose.yml -f docker-compose.addons.yml --profile ai-plus up
```

See [docs/ADDONS.md](docs/ADDONS.md) for the complete feature pack table and
runtime flags.

---

## Why aiops-agent?

|feature|K8sGPT|HolmesGPT|Keep|aiops-agent|
|---|---|---|---|---|
|Prometheus native webhook|No|No|Receives alerts|Yes + generic webhook|
|Alert normalization & routing|No|No|Basic|Yes, internal alert schema|
|AI + rule repair proposals|K8s only|Chat-based|No|Yes, with risk levels|
|Approval gate before execution|No|No|No|Yes, `GET/POST /api/v1/approvals`|
|Hardware dry-run (IPMI/Redfish/RAID/SMART/K8s)|No|No|No|Yes, `HARDWARE_EXECUTE_ENABLED=false` default|
|Auditable runbook result|No|No|No|Yes, every command and approval is traced|

---

## Documentation

- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** — Get a demo running in 5 minutes
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System design and alert flow
- **[docs/OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md)** — Safety flags, approval workflow, maintenance windows
- **[docs/BENCHMARKS.md](docs/BENCHMARKS.md)** — Performance and coverage numbers
- **[CONTRIBUTING.md](docs/CONTRIBUTING.md)** — How to contribute

---

## Safety first

All hardware actions and destructive software repairs require explicit approval
by default. Set `HARDWARE_EXECUTE_ENABLED=true` only after you have reviewed the
generated runbooks and understand the blast radius. See
[docs/OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md) for the full safety model.

---

## Phase 4：Web UI / SDK / CLI 使用方式

### Web UI

```bash
cd frontend
# 创建 .env.local，示例内容：
# NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
# NEXT_PUBLIC_INTERNAL_API_KEY=your-internal-key
npm install
npm run dev
```

打开 `http://localhost:3000`：

- `/alerts` — 告警事件列表（`GET /api/v1/alerts`）
- `/approval` — HITL 审批中心（`GET/PATCH/POST /api/v1/approvals`）
- `/audit` — 审计时间线（`GET /api/v1/audit`）
- `/history` — 修复历史与验证结果
- `/cost` — 成本看板（`GET /api/v1/cost/collect`, `/api/v1/cost/budget`）

### Python SDK

```bash
pip install -e sdk/python
```

```python
from aiops_agent_client import AgentClient

client = AgentClient(
    base_url="http://127.0.0.1:8000",
    internal_api_key="your-internal-key",
)
print(client.list_approvals())
client.approve("PROM-HighCPU-01")
client.close()
```

### CLI

```bash
python -m aiops_agent.cli --help
python -m aiops_agent.cli incidents
python -m aiops_agent.cli approve PROM-HighCPU-01
python -m aiops_agent.cli reject PROM-HighCPU-01 --reason "人工复核"
python -m aiops_agent.cli audit --limit 50
```

## License

[MIT](LICENSE)

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](docs/CODE_OF_CONDUCT.md).
