# -*- coding: utf-8 -*-
"""Real topology add-on microservice.

Maintains a graph of infrastructure/observability nodes and edges, with
BFS shortest-path and neighbor queries.
"""

import logging
import os
from collections import deque
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

SERVICE_NAME = "topology_service"
PORT = int(os.getenv("PORT", "8000"))

app = FastAPI(title=SERVICE_NAME.replace("_", " ").title())
logger = logging.getLogger(SERVICE_NAME)


class Node(BaseModel):
    id: str = Field(..., min_length=1)
    type: str = Field(..., pattern="^(service|host|database|load_balancer|kubernetes|unknown)$")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Edge(BaseModel):
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    relation: str = Field(default="depends_on")
    weight: float = Field(default=1.0, ge=0)


class HealthResponse(BaseModel):
    status: str
    service: str
    nodes: int
    edges: int


class NodesResponse(BaseModel):
    nodes: List[Node]


class EdgesResponse(BaseModel):
    edges: List[Edge]


class ShortestPathResponse(BaseModel):
    from_id: str
    to_id: str
    path: List[str]
    distance: float


class NeighborsResponse(BaseModel):
    node_id: str
    neighbors: List[Dict[str, Any]]


class Graph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.adj: Dict[str, List[Edge]] = {}

    def add_node(self, node: Node):
        self.nodes[node.id] = node
        if node.id not in self.adj:
            self.adj[node.id] = []

    def add_edge(self, edge: Edge):
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise HTTPException(status_code=400, detail="Both source and target nodes must exist")
        self.edges.append(edge)
        self.adj.setdefault(edge.source, []).append(edge)

    def shortest_path(self, from_id: str, to_id: str) -> ShortestPathResponse:
        if from_id not in self.nodes or to_id not in self.nodes:
            raise HTTPException(status_code=404, detail="Node not found")
        queue = deque([(from_id, [from_id], 0.0)])
        visited = {from_id}
        while queue:
            current, path, dist = queue.popleft()
            if current == to_id:
                return ShortestPathResponse(from_id=from_id, to_id=to_id, path=path, distance=dist)
            for edge in self.adj.get(current, []):
                if edge.target not in visited:
                    visited.add(edge.target)
                    queue.append((edge.target, path + [edge.target], dist + edge.weight))
        return ShortestPathResponse(from_id=from_id, to_id=to_id, path=[], distance=-1.0)

    def neighbors(self, node_id: str) -> NeighborsResponse:
        if node_id not in self.nodes:
            raise HTTPException(status_code=404, detail="Node not found")
        out = []
        for edge in self.adj.get(node_id, []):
            out.append(
                {
                    "node_id": edge.target,
                    "relation": edge.relation,
                    "weight": edge.weight,
                    "metadata": self.nodes.get(
                        edge.target, Node(id=edge.target, type="unknown")
                    ).metadata,
                }
            )
        return NeighborsResponse(node_id=node_id, neighbors=out)


graph = Graph()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok", service=SERVICE_NAME, nodes=len(graph.nodes), edges=len(graph.edges)
    )


@app.post("/nodes")
async def add_node(node: Node) -> Node:
    graph.add_node(node)
    logger.info("Added node %s of type %s", node.id, node.type)
    return node


@app.get("/nodes", response_model=NodesResponse)
async def list_nodes() -> NodesResponse:
    return NodesResponse(nodes=list(graph.nodes.values()))


@app.post("/edges")
async def add_edge(edge: Edge) -> Edge:
    graph.add_edge(edge)
    logger.info("Added edge %s -> %s (%s)", edge.source, edge.target, edge.relation)
    return edge


@app.get("/edges", response_model=EdgesResponse)
async def list_edges() -> EdgesResponse:
    return EdgesResponse(edges=graph.edges)


@app.get("/shortest_path", response_model=ShortestPathResponse)
async def shortest_path(from_id: str, to_id: str):
    return graph.shortest_path(from_id, to_id)


@app.get("/neighbors/{node_id}", response_model=NeighborsResponse)
async def neighbors(node_id: str):
    return graph.neighbors(node_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
