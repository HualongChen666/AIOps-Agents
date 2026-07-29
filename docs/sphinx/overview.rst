Overview
========

AIOps Agent is an intelligent operations platform that combines monitoring,
alerting, root-cause analysis and automated remediation.

Key Features
------------

- Real-time metric collection and anomaly detection
- AI-driven root cause analysis
- Automated repair and approval workflows
- OpenTelemetry-based observability
- Kubernetes / Helm deployment support
- Multi-language SDKs (Python, Go, Java)

Getting Started
---------------

Install dependencies and start the server:

.. code-block:: bash

    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8000

OpenAPI documentation is available at ``http://localhost:8000/docs``.
