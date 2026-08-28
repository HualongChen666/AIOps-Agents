# AIOps Plugin Examples

This directory contains example plugins demonstrating various plugin types and use cases for the AIOps platform.

## Available Examples

### 1. Custom Metrics Collector Plugin (`custom_metrics_collector.py`)

**Type**: Collector Plugin

**Description**: Collects custom metrics from external API endpoints and formats them for ingestion into the AIOps platform.

**Features**:
- Configurable API endpoint
- API key authentication support
- Custom metric prefix
- Flexible data transformation
- Error handling and logging

**Configuration**:
```yaml
api_endpoint: "https://api.example.com/metrics"
api_key: "your_api_key_here"
metric_prefix: "custom"
collection_interval: 60
```

**Usage**:
```python
from plugins.examples import CustomMetricsCollectorPlugin

plugin = CustomMetricsCollectorPlugin({
    "api_endpoint": "https://api.example.com/metrics",
    "api_key": "secret_key"
})

plugin.initialize()
result = await plugin.execute({"query": "cpu_usage"})
```

### 2. Anomaly Detector Plugin (`anomaly_detector.py`)

**Type**: Analyzer Plugin

**Description**: Detects anomalies in time-series data using statistical methods including z-score analysis, IQR, and isolation forest.

**Features**:
- Multiple detection methods (z-score, IQR, isolation forest)
- Configurable threshold
- Moving window analysis
- Severity classification
- Comprehensive statistics

**Configuration**:
```yaml
threshold: 3.0
window_size: 100
method: "zscore"
min_data_points: 20
```

**Usage**:
```python
from plugins.examples import AnomalyDetectorPlugin

plugin = AnomalyDetectorPlugin({
    "threshold": 3.0,
    "method": "zscore"
})

plugin.initialize()
result = await plugin.execute({
    "values": [10, 12, 11, 50, 13, 14, 12],
    "timestamps": ["2024-01-01T00:00:00", ...]
})
```

### 3. Slack Notifier Plugin (`slack_notifier.py`)

**Type**: Notifier Plugin

**Description**: Sends formatted notifications to Slack channels with support for different severity levels and custom message formatting.

**Features**:
- Custom Slack channel configuration
- Severity-based color coding
- Rich message formatting
- Custom fields support
- Bot customization

**Configuration**:
```yaml
webhook_url: "https://hooks.slack.com/services/..."
channel: "#alerts"
username: "AIOps Bot"
icon_emoji: ":robot_face:"
default_severity: "info"
```

**Usage**:
```python
from plugins.examples import SlackNotifierPlugin

plugin = SlackNotifierPlugin({
    "webhook_url": "https://hooks.slack.com/services/...",
    "channel": "#alerts"
})

plugin.initialize()
result = await plugin.execute({
    "title": "High CPU Usage",
    "message": "CPU usage exceeded 90%",
    "severity": "critical",
    "timestamp": "2024-01-01T00:00:00",
    "fields": [
        {"title": "Host", "value": "server-01"},
        {"title": "CPU", "value": "95%"}
    ]
})
```

## Installation

1. Copy the example plugin directory to your AIOps plugins folder:
```bash
cp -r plugins/examples /path/to/aiops/plugins/
```

2. Restart the AIOps platform:
```bash
systemctl restart aiops
```

3. Configure the plugin through the AIOps UI or API.

## Development

To create your own plugin based on these examples:

1. Copy the example that best matches your use case
2. Modify the plugin class name and metadata
3. Implement your custom logic in the `execute` method
4. Update the configuration schema as needed
5. Test your plugin thoroughly

## Testing

Run the plugin tests:
```bash
pytest tests/test_plugin_examples.py -v
```

## Support

For questions or issues with these examples:
- Check the main plugin documentation: `docs/PLUGIN_SYSTEM_GUIDE.md`
- Review the plugin API reference
- Contact the AIOps support team

## License

These examples are provided as part of the AIOps platform and follow the same license.