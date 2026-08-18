# -*- coding: utf-8 -*-
"""Real metrics monitoring add-on microservice.

Accepts time-series metric samples, stores them in memory, and provides
aggregation and Prometheus-compatible exposition.
"""

import logging
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from prometheus_client import CollectorRegistry, Counter, generate_latest
from pydantic import BaseModel, Field

SERVICE_NAME = "metrics_monitoring_service"
PORT = int(os.getenv("PORT", "8000"))
MAX_SAMPLES = int(os.getenv("MAX_SAMPLES", "10000"))

app = FastAPI(title=SERVICE_NAME.replace("_", " ").title())
logger = logging.getLogger(SERVICE_NAME)


timeseries_db: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
registry = CollectorRegistry()
api_counter = Counter("metrics_api_calls_total", "Total API calls", ["endpoint"], registry=registry)


class MetricSample(BaseModel):
    name: str = Field(..., min_length=1)
    value: float
    labels: Optional[Dict[str, str]] = Field(default_factory=dict)
    timestamp: Optional[float] = Field(default_factory=time.time)


class CollectRequest(BaseModel):
    samples: List[MetricSample]


class CollectResponse(BaseModel):
    accepted: int


class QueryResponse(BaseModel):
    metric: str
    start: Optional[float] = None
    end: Optional[float] = None
    count: int
    avg: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    sum: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    stored_samples: int


class PrometheusResponse(BaseModel):
    exposition: str


def _trim(name: str):
    if len(timeseries_db[name]) > MAX_SAMPLES:
        timeseries_db[name] = timeseries_db[name][-MAX_SAMPLES:]


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    total = sum(len(v) for v in timeseries_db.values())
    return HealthResponse(status="ok", service=SERVICE_NAME, stored_samples=total)


@app.post("/collect", response_model=CollectResponse)
async def collect(req: CollectRequest) -> CollectResponse:
    """Collect metric samples into the in-memory time series store."""
    for s in req.samples:
        timeseries_db[s.name].append(
            {
                "value": s.value,
                "labels": s.labels or {},
                "timestamp": s.timestamp or time.time(),
            }
        )
        _trim(s.name)
    api_counter.labels(endpoint="collect").inc(len(req.samples))
    logger.info("Collected %s metric samples", len(req.samples))
    return CollectResponse(accepted=len(req.samples))


@app.get("/query", response_model=QueryResponse)
async def query(
    metric: str = Query(..., min_length=1),
    start: Optional[float] = Query(default=None),
    end: Optional[float] = Query(default=None),
    agg: str = Query(default="avg", regex="^(avg|min|max|sum|count)$"),
    label_filter: Optional[str] = Query(default=None, description="key=value,key2=value2"),
) -> QueryResponse:
    """Aggregate stored samples for a metric over a time range."""
    if metric not in timeseries_db:
        raise HTTPException(status_code=404, detail="Metric not found")

    data = timeseries_db[metric]
    filtered = []
    labels = {}
    if label_filter:
        labels = dict(part.split("=", 1) for part in label_filter.split(",") if "=" in part)

    for d in data:
        ts = d["timestamp"]
        if start is not None and ts < start:
            continue
        if end is not None and ts > end:
            continue
        if labels and not all(d["labels"].get(k) == v for k, v in labels.items()):
            continue
        filtered.append(d["value"])

    if not filtered:
        return QueryResponse(
            metric=metric, start=start, end=end, count=0, avg=None, min=None, max=None, sum=None
        )

    if agg == "avg":
        result = {
            "avg": sum(filtered) / len(filtered),
            "min": min(filtered),
            "max": max(filtered),
            "sum": sum(filtered),
        }
    elif agg == "min":
        result = {"min": min(filtered), "avg": None, "max": None, "sum": None}
    elif agg == "max":
        result = {"max": max(filtered), "avg": None, "min": None, "sum": None}
    elif agg == "sum":
        result = {"sum": sum(filtered), "avg": None, "min": None, "max": None}
    else:  # count
        result = {"avg": None, "min": None, "max": None, "sum": None}

    api_counter.labels(endpoint="query").inc()
    return QueryResponse(metric=metric, start=start, end=end, count=len(filtered), **result)


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus-compatible metrics exposition."""
    api_counter.labels(endpoint="metrics").inc()
    return generate_latest(registry)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"), port=PORT)
