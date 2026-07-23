# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    import torch
    import torch.nn as nn
except Exception:
    torch: Optional[Any] = None  # type: ignore[no-redef]
    nn: Optional[Any] = None  # type: ignore[no-redef]
    logging.warning("torch 未安装，event_correlation 模块将使用占位实现。")

try:
    import dgl
except Exception:
    dgl: Optional[Any] = None  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

# ----------------------
# 简化的异构图模型占位实现
# ----------------------

if torch is not None and nn is not None:

    class SimpleHeteroGNN(nn.Module):
        """一个极简的异构图神经网络，仅用于占位。

        节点类型：
            - 'alert'（告警）
            - 'log'（日志）
            - 'metric'（指标）
            - 'biz'（业务事务）

        边类型：
            - ('alert', 'caused_by', 'log')
            - ('alert', 'related_to', 'metric')
            - ('alert', 'belongs_to', 'biz')

        实际生产中请使用更完整的特征、层数以及监督学习逻辑。
        """

        def __init__(self, hidden_dim: int = 64):
            super().__init__()
            self.hidden_dim = hidden_dim
            # 这里使用同配的线性层模拟消息传递
            self.linear = nn.Linear(hidden_dim, hidden_dim)
            self.activation = nn.ReLU()

        def forward(self, g: dgl.DGLHeteroGraph, features: Dict[str, torch.Tensor]):
            # 简单转发特征+线性变换，返回每类节点的 embedding
            out: Dict[str, torch.Tensor] = {}
            for ntype, feat in features.items():
                out[ntype] = self.activation(self.linear(feat))
            return out

else:

    class SimpleHeteroGNN:  # type: ignore[no-redef]
        """占位实现，当 torch 不可用时使用。"""

        def __init__(self, hidden_dim: int = 64):
            self.hidden_dim = hidden_dim

        def __call__(self, *args, **kwargs):
            return {}

        def eval(self):
            pass


# ----------------------
# 训练 / 推理占位函数
# ----------------------


def train_graph(train_data: List[Dict[str, Any]]) -> None:
    """占位训练函数。
    参数 ``train_data`` 预期为人工标注的事件关联样本列表，
    这里仅记录日志，不进行实际训练。
    """
    logger.info("[event_correlation] 开始占位训练，样本数=%d", len(train_data))
    # 实际实现应构造 DGL 异构图、特征矩阵、标签并训练模型
    # 此处仅保存一个空模型文件，防止后续加载报错
    if torch is not None:
        torch.save(SimpleHeteroGNN(), "core/event_correlation/model.pt")
    else:
        logger.warning("torch 未安装，跳过模型保存")
    logger.info("[event_correlation] 训练完成（占位），模型已保存至 model.pt")


def _build_hetero_graph(events: List[Dict[str, Any]]) -> Any:
    """构建异构图，如果 DGL 不可用则返回 None（占位实现）。"""
    if dgl is None:
        logger.warning("DGL 未安装，返回占位图结构")
        return None
    """根据事件列表构建简化的 DGL 异构图。
    每条 event 必须包含 ``event_id``、``source``、``type``（alert/log/metric/biz）字段。
    """
    # 按类型分组节点
    node_ids: Dict[str, List[int]] = {"alert": [], "log": [], "metric": [], "biz": []}
    for idx, ev in enumerate(events):
        etype = ev.get("type", "alert")
        if etype not in node_ids:
            etype = "alert"
        node_ids[etype].append(idx)
    # 创建空异构图并添加节点
    data = {}
    for ntype, ids in node_ids.items():
        data[(ntype, "self", ntype)] = (torch.tensor(ids), torch.tensor(ids))
    g = dgl.heterograph(data)
    return g


def infer_root_cause(event_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """使用已训练模型推断根因。
    输入：一批事件（告警/日志/指标/业务事务）
    输出：
        {
            "subgraph": {"nodes": [...], "edges": [...]},
            "root_causes": ["event_id1", "event_id2"],
        }
    """
    try:
        # 加载模型（若不存在则使用占位模型）
        model_path = "core/event_correlation/model.pt"
        if not torch.cuda.is_available():
            device = torch.device("cpu")
        else:
            device = torch.device("cuda")
        if torch is not None:
            model = torch.load(model_path, map_location=device, weights_only=True)
        else:
            logger.warning("torch 未安装，使用空模型代替")
            model = SimpleHeteroGNN()
        model.eval()
    except Exception as e:
        logger.error("[event_correlation] 加载模型失败: %s，使用空模型代替", e)
        model = SimpleHeteroGNN()
    # 构建异构图（占位实现，仅返回节点列表）
    g = _build_hetero_graph(event_batch)
    if g is None:
        # DGL 不可用时，直接返回空子图结构，根因以首个事件为默认
        subgraph = {
            "nodes": [
                {"id": ev.get("event_id"), "type": ev.get("type", "alert")} for ev in event_batch
            ],
            "edges": [],
        }
        # SECURITY: Check if event_batch is empty to avoid IndexError
        if not event_batch:
            return {"subgraph": subgraph, "root_causes": []}
        return {"subgraph": subgraph, "root_causes": [event_batch[0].get("event_id", "unknown")]}
    # 为每类节点创建随机特征向量（维度 hidden_dim）
    if torch is not None:
        features = {
            ntype: torch.randn(g.number_of_nodes(ntype), model.hidden_dim) for ntype in g.ntypes
        }
    else:
        # 使用零特征占位
        features = {ntype: None for ntype in g.ntypes}

    # 前向传播得到节点嵌入（实际模型会输出更有意义的向量）
    if torch is not None:
        with torch.no_grad():
            embeddings = model(g, features)
    else:
        logger.warning("torch 未安装，返回空嵌入占位")
        embeddings = {ntype: None for ntype in g.ntypes if g.ntypes}
    # 简单规则：若 alert 节点的 embedding L2 范数最大，则认为是根因
    root_causes: List[str] = []
    alert_embeddings = embeddings.get("alert")
    if alert_embeddings is not None and alert_embeddings.shape[0] > 0:
        norms = torch.norm(alert_embeddings, dim=1)
        max_idx = int(torch.argmax(norms).item())
        # 对应的事件在 batch 中的索引即为根因
        root_event = event_batch[max_idx]
        root_causes.append(root_event.get("event_id", f"idx_{max_idx}"))
    # 返回子图结构（仅节点 ID 与类型）
    subgraph = {
        "nodes": [
            {"id": ev.get("event_id"), "type": ev.get("type", "alert")} for ev in event_batch
        ],
        "edges": [],  # 占位，无具体关联边
    }
    return {"subgraph": subgraph, "root_causes": root_causes}


__all__ = ["SimpleHeteroGNN", "train_graph", "infer_root_cause"]
