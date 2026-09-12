# -*- coding: utf-8 -*-
"""
Topology Simple Router
拓扑简单路由，用于 /api/topology/* 路径

历史问题（已修复）：原实现 8 个端点全部返回**硬编码假拓扑**（固定 node-1/node-2、
固定边、health "healthy"、``last_updated`` 硬编码 "2026-09-01T11:00:00Z"）。现全部改为
调用真实的 ``core.topology_engine``（基于配置主机与告警边构建的真实图、真实依赖查询、
真实健康存储、真实 SPOF/校验分析）。无数据时如实返回空图，绝不伪造。
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from core import topology_engine as te
from core.authentication import get_current_active_user

router = APIRouter(prefix="/api/topology", tags=["拓扑"])


async def _load_graph() -> Dict[str, Any]:
    """Load the real full-link topology graph."""
    return await te.get_full_link_topology()


def _dependent_map(graph: Dict[str, Any]) -> Dict[str, List[str]]:
    """Derive a real dependency map (node -> direct downstream targets) from edges."""
    deps: Dict[str, List[str]] = {n["id"]: [] for n in graph.get("nodes", [])}
    for edge in graph.get("edges", []):
        src = edge.get("source")
        if src is not None:
            deps.setdefault(src, []).append(edge.get("target"))
    return deps


@router.get("/topology-graph")
async def get_topology_graph(user=Depends(get_current_active_user)):
    """获取拓扑图（真实图数据）"""
    graph = await _load_graph()
    return {
        "status": "success",
        "graph": {"nodes": graph.get("nodes", []), "edges": graph.get("edges", [])},
    }


@router.get("/topology-nodes")
async def get_topology_nodes(user=Depends(get_current_active_user)):
    """获取拓扑节点（真实节点 + 真实健康状态）"""
    graph = await _load_graph()
    nodes = [
        {
            "id": node.get("id"),
            "name": node.get("label", node.get("id")),
            "type": node.get("type", "service"),
            "status": te.get_node_health(node.get("id")),
        }
        for node in graph.get("nodes", [])
    ]
    return {"status": "success", "nodes": nodes}


@router.get("/topology-edges")
async def get_topology_edges(user=Depends(get_current_active_user)):
    """获取拓扑边（真实边数据）"""
    graph = await _load_graph()
    return {"status": "success", "edges": graph.get("edges", [])}


@router.get("/topology-dependencies")
async def get_topology_dependencies(user=Depends(get_current_active_user)):
    """获取拓扑依赖（由真实边推导）"""
    graph = await _load_graph()
    deps = _dependent_map(graph)
    return {
        "status": "success",
        "dependencies": [{"service": svc, "depends_on": targets} for svc, targets in deps.items()],
    }


@router.get("/topology-health")
async def get_topology_health(user=Depends(get_current_active_user)):
    """获取拓扑健康状态（真实节点健康）"""
    graph = await _load_graph()
    status = te.get_topology_status("default")
    node_health = {n.get("id"): te.get_node_health(n.get("id")) for n in graph.get("nodes", [])}
    known = [v for v in node_health.values() if v != "unknown"]
    if not known:
        overall = "unknown"
    elif any(v not in ("healthy", "up", "ok") for v in known):
        overall = "degraded"
    else:
        overall = "healthy"
    return {
        "status": "success",
        "health": {
            "overall": overall,
            "nodes": node_health,
            "node_count": status.get("node_count", len(node_health)),
            "last_updated": status.get("last_check"),
        },
    }


@router.get("/topology-metrics")
async def get_topology_metrics(user=Depends(get_current_active_user)):
    """获取拓扑指标（由真实图与健康数据计算）"""
    graph = await _load_graph()
    node_health = [te.get_node_health(n.get("id")) for n in graph.get("nodes", [])]
    healthy = sum(1 for h in node_health if h in ("healthy", "up", "ok"))
    unhealthy = sum(1 for h in node_health if h not in ("healthy", "up", "ok", "unknown"))
    return {
        "status": "success",
        "metrics": {
            "total_nodes": len(graph.get("nodes", [])),
            "total_edges": len(graph.get("edges", [])),
            "healthy_nodes": healthy,
            "unhealthy_nodes": unhealthy,
            "unknown_nodes": sum(1 for h in node_health if h == "unknown"),
        },
    }


@router.get("/topology-visualization")
async def get_topology_visualization(user=Depends(get_current_active_user)):
    """获取拓扑可视化（真实图坐标由前端布局计算，此处返回图结构）"""
    graph = await _load_graph()
    return {
        "status": "success",
        "visualization": {
            "layout": "force_directed",
            "nodes": graph.get("nodes", []),
            "edges": graph.get("edges", []),
        },
    }


@router.get("/topology-analysis")
async def get_topology_analysis(user=Depends(get_current_active_user)):
    """获取拓扑分析（真实 SPOF / 校验 / 关键路径）"""
    import networkx as nx

    graph = await _load_graph()
    validation = te.validate_topology(graph)

    g = nx.DiGraph()
    for node in graph.get("nodes", []):
        g.add_node(node.get("id"))
    for edge in graph.get("edges", []):
        g.add_edge(edge.get("source"), edge.get("target"))

    spof: List[str] = []
    if g.number_of_nodes() > 1:
        spof = list(nx.articulation_points(g.to_undirected()))

    critical_path: List[str] = []
    try:
        critical_path = nx.dag_longest_path(g) if nx.is_directed_acyclic_graph(g) else []
    except Exception:  # noqa: BLE001 - path is best-effort
        critical_path = []

    return {
        "status": "success",
        "analysis": {
            "critical_path": critical_path,
            "single_points_of_failure": spof,
            "warnings": validation.get("warnings", []),
            "recommendations": [
                f"消除单点故障: {node}" for node in spof
            ],
        },
    }
