# Workflow Templates

This directory contains pre-defined workflow templates for common AIOps scenarios.

## Template Structure

```yaml
name: template_name
description: Template description
nodes:
  - id: node_1
    name: Node 1 Name
    type: task
    config:
      param1: value1
    dependencies: []
  - id: node_2
    name: Node 2 Name
    type: task
    config:
      param2: value2
    dependencies: [node_1]
edges:
  - from: node_1
    to: node_2
```

## Available Templates

### alert_response.yaml
Alert response workflow for automated incident handling

### metric_analysis.yaml
Metric analysis workflow for performance monitoring

### log_analysis.yaml
Log analysis workflow for troubleshooting

### auto_remediation.yaml
Auto-remediation workflow for common issues
