# -*- coding: utf-8 -*-
import logging
from typing import Any, Dict, List

import networkx as nx

logger = logging.getLogger(__name__)

__all__ = [
    "build_topology_graph",
    "graph_to_dict",
    "TOPOLOGY_TYPES",
    "get_topology_status",
    "get_full_link_topology",
    "get_node_timeline",
    "update_node_health",
    "build_topology",
    "get_topology",
    "add_node",
    "add_edge",
    "remove_node",
    "remove_edge",
    "get_node_dependencies",
    "get_impact_analysis",
    "validate_topology",
    "insert_topology",
    "query_topology",
    "insert_node",
    "delete_node",
    "insert_edge",
    "delete_edge",
    "node_exists",
    "query_dependencies",
    "get_transitive_dependencies",
    "_topology_cache",
]

# ------------------------------------------------------------
# 核心拓扑图构建与转换工具（简化实现，满足 API 需求)
# ------------------------------------------------------------


def build_topology_graph(alerts: List[Dict[str, Any]]) -> nx.DiGraph:
    """根据告警列表构建有向拓扑图并计算 PageRank。

    参数
    ----
    alerts: List[Dict]
        每条告警应包含 ``source`` 与 ``target`` 键；
        可选 ``weight``（默认 1）表示边的权重。缺失字段/None 权重会被安全降级。

    返回
    ----
    nx.DiGraph
        包含 ``pagerank`` 节点属性的有向图。
    """
    G = nx.DiGraph()
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        src = alert.get("source") or "unknown"
        dst = alert.get("target") or src
        weight = alert.get("weight") or 1
        if not isinstance(weight, (int, float)):
            weight = 1
        G.add_edge(src, dst, weight=weight)
    # 计算 PageRank（使用权重）
    pr = nx.pagerank(G, weight="weight") if G.number_of_nodes() > 0 else {}
    nx.set_node_attributes(G, pr, "pagerank")
    return G


def graph_to_dict(G: nx.DiGraph) -> Dict[str, List[Dict[str, Any]]]:
    """将 ``nx.DiGraph`` 转换为 AntV G6 所需的 ``nodes``/``edges`` 结构。"""
    nodes = [
        {"id": n, "label": str(n), "pagerank": round(data.get("pagerank", 0), 4)}
        for n, data in G.nodes(data=True)
    ]
    edges = [
        {"source": u, "target": v, "weight": data.get("weight", 1)}
        for u, v, data in G.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}


# ------------------------------------------------------------
# API 所需的占位实现（后续可接入真实业务逻辑）
# ------------------------------------------------------------

# 示例拓扑类型映射，可在实际实现中扩展
TOPOLOGY_TYPES: Dict[str, str] = {
    "default": "默认拓扑",
    "service": "服务依赖",
    "network": "网络拓扑",
}


def get_topology_status(topo_key: str) -> Dict[str, Any]:
    """返回指定拓扑的简要运行状态（占位实现）。"""
    # 实际实现应返回节点计数、活跃流等信息，这里返回空结构防止 500 错误
    return {"node_count": 0, "active_flows": []}


async def get_full_link_topology(topo_key: str | None = None) -> Dict[str, Any]:
    """返回全链路拓扑的完整图数据。

    - 若有告警数据，则基于告警边构建图。
    - 同时将 ``config.LINUX_HOSTS`` 中的主机加入拓扑，形成
      ``agent -> host -> internet`` 的基础链路（即使没有告警，
      也能展示真实的主机节点）。
    - 当 ``topo_key`` 被指定时仍保持兼容，当前实现不使用该参数。
    """
    try:
        # -----------------------------------------------------
        # 1️⃣ 收集告警生成的边（如果有的话）
        # -----------------------------------------------------
        from core.db_engine import alert_repository

        recent_alerts = await alert_repository.get_recent(limit=20)
        alerts_for_graph: List[Dict[str, Any]] = []
        for a in recent_alerts:
            if isinstance(a, dict) and "source" in a and "target" in a:
                alerts_for_graph.append(
                    {
                        "source": a["source"],
                        "target": a["target"],
                        "weight": a.get("weight", 1),
                    }
                )

        # -----------------------------------------------------
        # 2️⃣ 加入配置的主机节点并建立基础链路
        # -----------------------------------------------------
        from config import LINUX_HOSTS

        # 确保有最小的 agent / internet / detect 节点（用于占位）
        base_nodes = {"agent", "internet", "detect"}
        # 将每个 LINUX_HOST 添加为节点，并连线: agent -> host -> internet
        for host_cfg in LINUX_HOSTS:  # type: ignore
            if isinstance(host_cfg, dict):
                host_name = host_cfg.get("host_name") or host_cfg.get("name") or str(host_cfg)
            else:
                host_name = str(host_cfg)
            # 防止空或重复名称
            if not host_name:
                continue
            base_nodes.add(host_name)
            alerts_for_graph.append({"source": "agent", "target": host_name, "weight": 1})
            alerts_for_graph.append({"source": host_name, "target": "internet", "weight": 1})

        # 若仍然没有任何边（没有告警且没有主机），使用最小示例防止前端错误
        if not alerts_for_graph:
            alerts_for_graph = [
                {"source": "agent", "target": "internet", "weight": 1},
                {"source": "detect", "target": "agent", "weight": 1},
            ]

        # -----------------------------------------------------
        # 3️⃣ 构建图并返回结构化数据
        # -----------------------------------------------------
        G = build_topology_graph(alerts_for_graph)
        topo_dict = graph_to_dict(G)
        topo_dict["stats"] = [  # type: ignore
            {
                "node_count": len(topo_dict["nodes"]),
                "edge_count": len(topo_dict["edges"]),
            }
        ]
        return topo_dict
    except Exception as e:
        logger.error(f"构建全链路拓扑失败: {e}", exc_info=True)
        # 回退到空结构，前端能安全渲染
        return {"nodes": [], "edges": []}


def get_node_timeline(node_id: str) -> Dict[str, Any]:
    """获取单个节点的时间线信息（占位实现）。"""
    return {"events": []}


def update_node_health(node_id: str, status: str) -> bool:
    """Update node health status."""
    return True


# ------------------------------------------------------------
# 数据库/缓存占位接口（测试中会被 patch）
# ------------------------------------------------------------

_topology_cache: Dict[str, Any] = {}


async def insert_topology(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    """Placeholder: persist topology and return an id."""
    return "topology-001"


async def query_topology(topology_id: str) -> Any:
    """Placeholder: fetch topology by id."""
    return None


async def insert_node(node: Dict[str, Any]) -> bool:
    """Placeholder: insert a node."""
    return True


async def delete_node(node_id: str) -> bool:
    """Placeholder: delete a node."""
    return True


async def insert_edge(edge: Dict[str, Any]) -> bool:
    """Placeholder: insert an edge."""
    return True


async def delete_edge(edge_id: str) -> bool:
    """Placeholder: delete an edge."""
    return True


async def node_exists(node_id: str) -> bool:
    """Placeholder: check if a node exists."""
    return True


async def query_dependencies(node_id: str) -> List[Dict[str, Any]]:
    """Placeholder: return direct dependencies of a node."""
    return []


async def get_transitive_dependencies(node_id: str) -> List[str]:
    """Placeholder: return transitive dependencies of a node."""
    return []


# ------------------------------------------------------------
# Topology CRUD / validation functions used by root tests
# ------------------------------------------------------------


async def build_topology(
    nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Build and persist a topology, validating nodes and cycles."""
    for node in nodes:
        if not isinstance(node, dict) or not str(node.get("id", "")).strip():
            return {"success": False, "error": "invalid node: missing or empty id"}

    G = nx.DiGraph()
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        src = edge.get("source")
        tgt = edge.get("target")
        if src and tgt:
            G.add_edge(src, tgt)

    if not nx.is_directed_acyclic_graph(G):
        return {"success": False, "error": "circular dependency detected"}

    try:
        topology_id = await insert_topology(nodes, edges)
        return {"success": True, "topology_id": topology_id}
    except Exception as e:
        logger.error(f"build_topology failed: {e}")
        return {"success": False, "error": str(e)}


async def get_topology(topology_id: str) -> Dict[str, Any]:
    """Fetch topology by id, checking in-memory cache first."""
    if not topology_id:
        return {"success": False, "error": "invalid topology id"}

    if topology_id in _topology_cache:
        return {"success": True, "topology": _topology_cache[topology_id], "from_cache": True}

    topology = await query_topology(topology_id)
    if not topology:
        return {"success": False, "error": "topology not found"}
    return {"success": True, "topology": topology, "from_cache": False}


async def add_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """Add a node after duplicate check."""
    if not isinstance(node, dict) or not node.get("id"):
        return {"success": False, "error": "invalid node"}
    inserted = await insert_node(node)
    if not inserted:
        return {"success": False, "error": "duplicate node"}
    return {"success": True}


async def remove_node(node_id: str) -> Dict[str, Any]:
    """Remove a node if it has no dependencies."""
    dependencies = await get_node_dependencies(node_id)
    if dependencies:
        return {"success": False, "error": "node has dependencies"}
    deleted = await delete_node(node_id)
    if not deleted:
        return {"success": False, "error": "failed to remove node"}
    return {"success": True}


async def add_edge(edge: Dict[str, Any]) -> Dict[str, Any]:
    """Add an edge after source/target node existence check."""
    if not isinstance(edge, dict) or not edge.get("source") or not edge.get("target"):
        return {"success": False, "error": "invalid edge"}
    src_exists = await node_exists(edge["source"])
    tgt_exists = await node_exists(edge["target"])
    if not src_exists or not tgt_exists:
        return {"success": False, "error": "node not found"}
    inserted = await insert_edge(edge)
    if not inserted:
        return {"success": False, "error": "failed to add edge"}
    return {"success": True}


async def remove_edge(edge_id: str) -> Dict[str, Any]:
    """Remove an edge by id."""
    deleted = await delete_edge(edge_id)
    if not deleted:
        return {"success": False, "error": "failed to remove edge"}
    return {"success": True}


async def get_node_dependencies(node_id: str) -> List[Dict[str, Any]]:
    """Return direct dependencies for a node."""
    return await query_dependencies(node_id)


async def get_impact_analysis(node_id: str) -> Dict[str, Any]:
    """Return direct and transitive impact for a node."""
    direct = await query_dependencies(node_id) or []
    transitive = await get_transitive_dependencies(node_id) or []
    return {"direct_impact": direct, "transitive_impact": transitive}


def validate_topology(topology: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a topology and warn about orphan nodes."""
    if not isinstance(topology, dict):
        return {"valid": False, "error": "invalid topology"}
    nodes = topology.get("nodes", [])
    edges = topology.get("edges", [])
    connected: set[str] = set()
    for edge in edges:
        if isinstance(edge, dict):
            if edge.get("source"):
                connected.add(edge["source"])
            if edge.get("target"):
                connected.add(edge["target"])
    warnings: List[str] = []
    for node in nodes:
        if isinstance(node, dict) and node.get("id") not in connected:
            warnings.append(f"orphan node: {node.get('id')}")
    return {"valid": True, "warnings": warnings}
