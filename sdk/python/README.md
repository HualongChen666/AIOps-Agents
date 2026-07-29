# aiops-agent-client

Official Python SDK for the AIOps SRE Agent.

## Install

```bash
pip install -e sdk/python
```

## Usage

```python
from aiops_agent_client import AgentClient

client = AgentClient(
    base_url="http://127.0.0.1:8000",
    internal_api_key="your-internal-key",
)

# list pending approvals
approvals = client.list_approvals()

# approve an incident
client.approve("PROM-HighCPU-01")

# view audit log
events = client.get_audit(limit=50)

client.close()
```
