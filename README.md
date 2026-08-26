# AIOps SRE Agent

![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=flat-square)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?style=flat-square)
![Docker Compose](https://img.shields.io/badge/docker--compose-ready-2496ED.svg?style=flat-square)
![Coverage](https://img.shields.io/badge/coverage-90.18%25-brightgreen.svg?style=flat-square)
![Tests](https://img.shields.io/badge/tests-99.9%25-brightgreen.svg?style=flat-square)

> **Enterprise-grade Autonomous SRE Agent with Platform-scale Capabilities**

AIOps SRE Agent is an intelligent, self-learning operations agent that transforms monitoring alerts into automated, approved, and auditable repairs. Built with platform-scale architecture but focused on autonomous decision-making, the agent continuously learns from incidents to improve its repair capabilities while maintaining enterprise-grade safety and compliance.

## 🚀 Key Features

- **🤖 AI-Powered Analysis**: MiniMax LLM integration with multi-model support (OpenAI, Anthropic) for intelligent root cause analysis and repair recommendations
- **🔔 Multi-Source Alert Ingestion**: Native support for Prometheus, Grafana, Datadog, Zabbix, CloudWatch, and custom webhooks
- **🛡️ Safety-First Execution**: Command guard system with 50+ risk rules, approval gates, and dry-run mode for all hardware operations
- **🔍 Comprehensive Observability**: Metrics, logs, distributed tracing, and APM with OpenTelemetry integration
- **📊 SLO/SLA Management**: Service level objectives monitoring, error budget tracking, and compliance reporting
- **🌐 Service Topology**: Automatic service discovery, dependency mapping, and topology visualization
- **🏗️ Modular Architecture**: 7 shared engines supporting 45+ addons for extensible functionality
- **🔐 Enterprise Security**: Multi-tenant support, RBAC/ABAC, MFA, SSO, and compliance (GDPR, SOC2)
- **🔄 Workflow Automation**: LangGraph-based DSL workflows, Saga pattern, and state machine orchestration
- **📈 Business Impact**: Business metrics, capacity planning, and cost optimization

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Core Features](#core-features)
- [Add-on Packs](#add-on-packs)
- [Installation](#installation)
- [Configuration](#configuration)
- [Development](#development)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (optional)
- PostgreSQL 14+ (optional, SQLite for development)
- Redis 7+ (optional, in-memory fallback available)

### Installation

#### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/HualongChen666/AIOps-Agents.git
cd AIOps-Agents
cp .env.example .env
docker compose up -d
```

Access the API documentation at `http://localhost:8000/docs`

#### Option 2: Local Development

```bash
git clone https://github.com/HualongChen666/AIOps-Agents.git
cd AIOps-Agents
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
python main.py
```

### First Alert Test

```bash
curl -X POST http://localhost:8000/api/v1/alerts/prometheus \
  -H "Content-Type: application/json" \
  -d @examples/prometheus_alert.json
```

---

## 🏗️ Architecture

### Agent Closed-Loop Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Monitoring Systems                        │
│  Prometheus │ Grafana │ Datadog │ Zabbix │ CloudWatch     │
└────────────────────┬────────────────────────────────────────┘
                     │ Webhooks
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Alert Ingestion & Normalization Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Alert Parser │  │ Normalizer   │  │ Classifier   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  AI Analysis & Decision Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ LLM Analysis │  │ RAG Retrieval│  │ Knowledge Gr │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Approval & Safety Layer                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Approval Gate│  │ Risk Engine  │  │ Command Guard│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Execution & Repair Layer                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Repair Engine│  │ Saga Coord   │  │ Rollback     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Audit & Learning Layer                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Audit Trail  │  │ Knowledge Acq│  │ Model Update │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Knowledge Base & Continuous Improvement                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Vector Store │  │ Experience DB│  │ Feedback Loop│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

- **Alert Ingestion & Normalization**: Multi-source alert ingestion, unified alert model, intelligent classification
- **AI Analysis & Decision**: LLM-powered root cause analysis, RAG retrieval, knowledge graph reasoning
- **Approval & Safety**: Multi-level approval gates, risk assessment, command guard system
- **Execution & Repair**: Automated repair execution, saga coordination, rollback mechanisms
- **Audit & Learning**: Comprehensive audit trails, knowledge acquisition, model updates
- **Knowledge Base & Continuous Improvement**: Vector storage, experience database, feedback learning loop

---

## 🎯 Core Features

### Alert Management

- **Multi-Source Ingestion**: Prometheus, Grafana, Datadog, Zabbix, CloudWatch webhooks
- **Alert Normalization**: Unified alert model across different monitoring systems
- **Intelligent Deduplication**: N-2 deduplication, M-4 SSH brute force detection, M-5 dynamic thresholds
- **Smart Classification**: AI-powered alert classification and severity assessment
- **Alert Routing**: Rule-based and AI-driven intelligent alert routing
- **Escalation**: Automatic escalation with on-call team management

### AI-Powered Analysis

- **LLM Integration**: MiniMax, OpenAI, Anthropic multi-model support
- **RAG Retrieval**: Vector database (Qdrant) with semantic search
- **Knowledge Graph**: Dependency graphs, fault graphs, reasoning engine
- **Causal Analysis**: Causal graph construction, GNN-based root cause inference
- **Call Chain Analysis**: Distributed tracing, dependency mapping
- **Cost Optimization**: LLM cost monitoring, budget control, model routing

### Automated Repair

- **Multi-Platform Support**: Windows PowerShell, Linux Bash, Kubernetes, Docker
- **Hardware Remediation**: IPMI, Redfish, RAID, SMART operations
- **Software Repairs**: Service restart, configuration changes, log cleanup
- **Command Guard System**: 50+ risk rules, safety barriers, platform-specific controls
- **Approval Gates**: Multi-level approval, conditional approval, maintenance windows
- **Saga Pattern**: Distributed transactions, compensation mechanisms
- **Dry-Run Mode**: Safe preview before execution (default for hardware)

### Observability

- **Metrics Monitoring**: Prometheus integration, custom KPIs, business metrics
- **Log Management**: Windows Event Log, Linux remote logs, ELK Stack integration
- **Distributed Tracing**: OpenTelemetry integration, call chain visualization
- **APM**: Code profiling, dependency analysis, real user monitoring (RUM)
- **Real-Time Monitoring**: SSE streaming, real-time metrics, alert dashboards

### SLO/SLA Management

- **SLO Configuration**: Target setting, window configuration, aggregation strategies
- **Error Budget Tracking**: Real-time budget monitoring, burn rate calculation
- **SLA Reporting**: Compliance reports, historical trends, KPI dashboards
- **Capacity Planning**: Capacity forecasting, resource optimization, auto-scaling

### Security & Compliance

- **Multi-Tenancy**: Tenant isolation, resource separation, permission isolation
- **Authentication**: JWT tokens, OAuth2, OIDC, SSO integration
- **Authorization**: RBAC, ABAC, role-based access control
- **MFA Support**: TOTP, multi-factor authentication
- **Compliance**: GDPR compliance, SOC2 compliance, audit trails
- **Security Scanning**: Vulnerability scanning, penetration testing, security policies

### Workflow Automation

- **DSL Workflows**: Domain-specific language for workflow definition
- **LangGraph Engine**: Workflow orchestration, state management, visualization
- **Saga Coordination**: Distributed transaction coordination, compensation
- **Task Scheduling**: Temporal integration, Prefect integration, Cron scheduling
- **Kafka Streaming**: Real-time stream processing, Flink integration

---

## 🔌 Add-on Packs

The platform supports modular add-on packs that can be enabled/disabled via environment variables:

### AI Plus Pack

- **RAG Service**: Vector database integration, semantic search, knowledge base
- **LLM Router Service**: Intelligent model routing, cost optimization, load balancing
- **Knowledge Graph Service**: Dependency graphs, fault graphs, reasoning engine

### Observability & Topology Pack

- **Topology Service**: Service topology, dependency mapping, impact analysis
- **Metrics Monitoring**: Advanced metrics collection, custom dashboards
- **Tracing Service**: Distributed tracing, performance analysis
- **Log Aggregation**: Centralized logging, log search, log analysis

### SRE Operations Pack

- **Incident Response**: Incident management, escalation, collaboration
- **Workflow Service**: Workflow automation, state machine, DSL execution

### Multi-Cloud & Integrations Pack

- **Cloud Providers**: AWS, Azure, GCP integrations
- **Monitoring Tools**: Datadog, Grafana, ELK Stack integrations
- **ITSM Tools**: ServiceNow, Jira, Zendesk integrations

### Security & Compliance Pack

- **Security Scanning**: Vulnerability scanning, security policies
- **Penetration Testing**: Automated security testing
- **Compliance Management**: GDPR, SOC2 compliance reporting

### Infrastructure & Plugin Ecosystem Pack

- **Plugin System**: Plugin development SDK, plugin marketplace
- **Sharding**: Data sharding, distributed storage
- **I18N**: Internationalization, multi-language support

### Documentation & Tooling Pack

- **Documentation Generator**: Auto documentation, API docs
- **Test Framework**: Test automation, coverage analysis

### Enabling/Disabling Add-ons

Add-ons are controlled by environment variables in `config.py`:

```bash
# Disable specific add-ons
RAG_ENABLED=false
LLM_ROUTER_ENABLED=false
TOPOLOGY_ENABLED=false
TRACING_ENABLED=false
```

Or use Docker Compose profiles:

```bash
docker compose -f docker-compose.yml -f docker-compose.addons.yml --profile ai-plus up
```

---

## 📦 Installation

### System Requirements

- **Python**: 3.10 or higher
- **Database**: PostgreSQL 14+ (recommended) or SQLite (development)
- **Cache**: Redis 7+ (recommended) or in-memory fallback
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 20GB disk space minimum

### Installation Methods

#### Method 1: Docker Compose (Production)

```bash
git clone https://github.com/HualongChen666/AIOps-Agents.git
cd AIOps-Agents
cp .env.example .env
# Edit .env with your configuration
docker compose up -d
```

#### Method 2: Python Package (Development)

```bash
git clone https://github.com/HualongChen666/AIOps-Agents.git
cd AIOps-Agents
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
python main.py
```

#### Method 3: Kubernetes (Production)

```bash
kubectl apply -f k8s/
# Configure environment variables in k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
```

---

## ⚙️ Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=aiops

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# AI Configuration
AI_API_KEY=your_api_key
AI_BASE_URL=https://api.minimaxi.com/v1
RAG_ENABLED=true
LLM_ROUTER_ENABLED=true

# Feature Flags
TOPOLOGY_ENABLED=true
TRACING_ENABLED=true
LOG_AGGREGATION_ENABLED=true
WORKFLOW_ENABLED=true
SECURITY_SCANNING_ENABLED=true

# Security
JWT_SECRET_KEY=your_secret_key
INTERNAL_API_KEY=your_internal_key
```

### Feature Flags

Control platform features via environment variables:

| Feature | Environment Variable | Default |
| --------- | --------------------- | --------- |
| RAG | `RAG_ENABLED` | `true` |
| LLM Router | `LLM_ROUTER_ENABLED` | `true` |
| Topology | `TOPOLOGY_ENABLED` | `true` |
| Tracing | `TRACING_ENABLED` | `true` |
| Workflows | `WORKFLOW_ENABLED` | `true` |
| Security Scanning | `SECURITY_SCANNING_ENABLED` | `true` |

---

## 🛠️ Development

### Setup Development Environment

```bash
git clone https://github.com/HualongChen666/AIOps-Agents.git
cd AIOps-Agents
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests --cov=. --cov-branch

# Run specific test suite
pytest tests/core/
pytest tests/api/
```

### Code Quality

```bash
# Format code
black .
isort .

# Type checking
mypy core/

# Linting
flake8 core/
```

### Project Structure

```
aiops-sre-agent/
├── api/                    # FastAPI routers and endpoints
├── core/                   # Core engines and business logic
│   ├── ai/                # AI engines (LLM, RAG, knowledge graph)
│   ├── agent/             # Agent framework
│   ├── alert_providers/   # Alert source integrations
│   └── ...
├── modules/                # Analysis and execution modules
├── services/               # Microservice implementations
├── extensions/             # Add-on packs and engines
├── tests/                  # Test suite
├── main.py                 # Application entry point
└── config.py               # Configuration management
```

---

## 📚 Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** — Get started in 5 minutes
- **[Architecture Documentation](docs/ARCHITECTURE.md)** — System design and data flow
- **[Operator Guide](docs/OPERATOR_GUIDE.md)** — Safety flags, approval workflow
- **[Capabilities Matrix](docs/CAPABILITIES.md)** — Feature comparison
- **[API Documentation](http://localhost:8000/docs)** — Interactive API docs
- **[Add-ons Guide](docs/ADDONS.md)** — Add-on packs configuration

---

## 🗺️ Roadmap

### v1.0 (Current)

- ✅ Core alert processing and normalization
- ✅ AI-powered root cause analysis
- ✅ Multi-platform repair execution
- ✅ Safety-first execution model
- ✅ Comprehensive observability
- ✅ Enterprise security features

### v1.1 (Planned)

- 🔄 Enhanced mobile app
- 🔄 Advanced anomaly detection
- 🔄 Predictive maintenance
- 🔄 Multi-region deployment
- 🔄 Enhanced plugin marketplace

### v2.0 (Future)

- 🔄 Full AIOps automation
- 🔄 Self-healing infrastructure
- 🔄 Predictive capacity planning
- 🔄 Advanced compliance automation
- 🔄 Enterprise SaaS offering

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- AI powered by [MiniMax](https://api.minimaxi.com/)
- Vector storage by [Qdrant](https://qdrant.tech/)
- Observability by [OpenTelemetry](https://opentelemetry.io/)

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/HualongChen666/AIOps-Agents/issues)
- **Discussions**: [GitHub Discussions](https://github.com/HualongChen666/AIOps-Agents/discussions)

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=HualongChen666/AIOps-Agents&type=Date)](https://api.star-history.com/svg?repos=HualongChen666/AIOps-Agents&type=Date)
