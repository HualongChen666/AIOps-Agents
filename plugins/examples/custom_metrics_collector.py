# -*- coding: utf-8 -*-
"""
Example Plugin 1: Custom Metrics Collector

This plugin demonstrates how to collect custom metrics from an external API
and ingest them into the AIOps platform.
"""

import aiohttp
import logging
from typing import Dict, Any, Optional
from core.plugin_system import BasePlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class CustomMetricsCollectorPlugin(BasePlugin):
    """
    Custom Metrics Collector Plugin
    
    Collects custom metrics from a configurable API endpoint
    and formats them for ingestion into the AIOps platform.
    """
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        return PluginMetadata(
            name="custom_metrics_collector",
            version="1.0.0",
            description="Collects custom metrics from external API endpoints",
            author="AIOps Team",
            plugin_type=PluginType.COLLECTOR,
            dependencies=["aiohttp"],
            config_schema={
                "type": "object",
                "properties": {
                    "api_endpoint": {
                        "type": "string",
                        "format": "uri",
                        "description": "API endpoint to collect metrics from"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "API key for authentication"
                    },
                    "metric_prefix": {
                        "type": "string",
                        "default": "custom",
                        "description": "Prefix for metric names"
                    },
                    "collection_interval": {
                        "type": "integer",
                        "minimum": 10,
                        "maximum": 3600,
                        "default": 60,
                        "description": "Collection interval in seconds"
                    }
                },
                "required": ["api_endpoint"]
            }
        )
    
    def initialize(self) -> bool:
        """Initialize the plugin"""
        if not self.validate_config(["api_endpoint"]):
            logger.error("Invalid configuration: missing required fields")
            return False
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._metric_prefix = self.config.get("metric_prefix", "custom")
        self._collection_interval = self.config.get("collection_interval", 60)
        
        logger.info(f"CustomMetricsCollectorPlugin initialized with prefix: {self._metric_prefix}")
        self._is_initialized = True
        return True
    
    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin logic to collect metrics"""
        if not self._is_initialized:
            return {"status": "error", "error": "Plugin not initialized"}
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        try:
            # Prepare request headers
            headers = {}
            if "api_key" in self.config:
                headers["Authorization"] = f"Bearer {self.config['api_key']}"
            
            # Fetch metrics from API
            async with self._session.get(
                self.config["api_endpoint"],
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": f"API returned status {response.status}"
                    }
                
                api_data = await response.json()
            
            # Transform API data to AIOps metric format
            metrics = self._transform_metrics(api_data)
            
            return {
                "status": "success",
                "metrics": metrics,
                "count": len(metrics),
                "metric_prefix": self._metric_prefix
            }
            
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return {"status": "error", "error": f"HTTP error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
    
    def _transform_metrics(self, api_data: Dict[str, Any]) -> list:
        """Transform API data to AIOps metric format"""
        metrics = []
        
        # Handle different API response formats
        if isinstance(api_data, dict):
            # Format 1: {"metrics": [{"name": "...", "value": ...}]}
            if "metrics" in api_data:
                for metric in api_data["metrics"]:
                    metrics.append({
                        "name": f"{self._metric_prefix}.{metric.get('name', 'unknown')}",
                        "value": metric.get("value", 0),
                        "timestamp": metric.get("timestamp", None),
                        "labels": metric.get("labels", {})
                    })
            
            # Format 2: {"cpu": 50, "memory": 80}
            else:
                for key, value in api_data.items():
                    if isinstance(value, (int, float)):
                        metrics.append({
                            "name": f"{self._metric_prefix}.{key}",
                            "value": value,
                            "timestamp": None,
                            "labels": {}
                        })
        
        elif isinstance(api_data, list):
            # Format 3: [{"name": "...", "value": ...}]
            for item in api_data:
                if isinstance(item, dict):
                    metrics.append({
                        "name": f"{self._metric_prefix}.{item.get('name', 'unknown')}",
                        "value": item.get("value", 0),
                        "timestamp": item.get("timestamp", None),
                        "labels": item.get("labels", {})
                    })
        
        return metrics
    
    def close(self) -> None:
        """Close the plugin and release resources"""
        if self._session:
            self._session.close()
            self._session = None
        
        self._is_initialized = False
        logger.info("CustomMetricsCollectorPlugin closed")