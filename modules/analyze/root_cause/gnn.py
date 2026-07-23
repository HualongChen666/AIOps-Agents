# -*- coding: utf-8 -*-
"""
Heterogeneous GNN Model for Root Cause Analysis
基于DGL的异构图神经网络模型，用于根因推断

功能:
- 异构图神经网络模型
- 节点特征嵌入
- 边类型聚合
- 根因预测
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, Union, cast  # noqa: F401

import numpy as np

try:
    import dgl
    import dgl.nn as dglnn
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    DGL_AVAILABLE = True
except ImportError:
    DGL_AVAILABLE = False
    dgl = None  # type: ignore[assignment]
    dglnn = None  # type: ignore[assignment]
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
    F = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class HeteroGNNLayer(nn.Module):
    """
    异构图神经网络层

    使用RGCN（Relational Graph Convolutional Network）处理异构图。
    """

    def __init__(
        self,
        in_feats: Dict[str, int],
        out_feats: int,
        etypes: List[str],
        num_bases: Optional[int] = None,
    ):
        super().__init__()
        if not DGL_AVAILABLE:
            raise ImportError(
                "DGL and PyTorch are not installed. Install with: pip install dgl torch"
            )

        self.in_feats = in_feats
        self.out_feats = out_feats
        self.etypes = etypes

        # RGCN层
        self.conv = dglnn.HeteroGraphConv(
            {etype: dglnn.GraphConv(in_feats, out_feats) for etype in etypes}, aggregate="mean"
        )

    def forward(
        self, g: dgl.DGLHeteroGraph, features: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        """
        前向传播

        参数:
            g: 异构图
            features: 节点特征字典 {ntype: tensor}

        返回:
            更新后的节点特征
        """
        return cast(Dict[str, torch.Tensor], self.conv(g, features))


class HeterogeneousGNNModel(nn.Module):
    """
    异构图神经网络模型

    用于根因推断的GNN模型，支持多种节点类型和边类型。

    参数:
        node_types: 节点类型列表
        edge_types: 边类型列表
        in_feats: 输入特征维度字典 {ntype: dim}
        hidden_feats: 隐藏层维度
        out_feats: 输出维度
        num_layers: GNN层数
        dropout: Dropout概率
    """

    def __init__(
        self,
        node_types: List[str],
        edge_types: List[str],
        in_feats: Dict[str, int],
        hidden_feats: int = 64,
        out_feats: int = 32,
        num_layers: int = 2,
        dropout: float = 0.5,
    ):
        super().__init__()

        if not DGL_AVAILABLE:
            raise ImportError(
                "DGL and PyTorch are not installed. Install with: pip install dgl torch"
            )

        self.node_types = node_types
        self.edge_types = edge_types
        self.in_feats = in_feats
        self.hidden_feats = hidden_feats
        self.out_feats = out_feats
        self.num_layers = num_layers
        self.dropout = dropout

        # 特征嵌入层（将不同维度的输入特征映射到统一维度）
        self.embeddings = nn.ModuleDict(
            {ntype: nn.Linear(in_feats[ntype], hidden_feats) for ntype in node_types}
        )

        # GNN层
        self.gnn_layers = nn.ModuleList()
        for i in range(num_layers):
            self.gnn_layers.append(
                HeteroGNNLayer(
                    in_feats={ntype: hidden_feats for ntype in node_types},
                    out_feats=hidden_feats,
                    etypes=edge_types,
                )
            )

        # 输出层
        self.output_layers = nn.ModuleDict(
            {ntype: nn.Linear(hidden_feats, out_feats) for ntype in node_types}
        )

        # 分类层（用于根因预测）
        self.classifier = nn.Linear(out_feats, 2)  # 2类：根因/非根因

        self.dropout_layer = nn.Dropout(dropout)

    def forward(
        self, g: dgl.DGLHeteroGraph, features: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        """
        前向传播

        参数:
            g: 异构图
            features: 节点特征字典 {ntype: tensor}

        返回:
            节点嵌入字典 {ntype: tensor}
        """
        # 特征嵌入
        h = {}
        for ntype in self.node_types:
            if ntype in features:
                h[ntype] = self.embeddings[ntype](features[ntype])
            else:
                # 如果没有特征，使用随机初始化
                h[ntype] = torch.zeros(
                    g.num_nodes(ntype), self.hidden_feats, device=next(self.parameters()).device
                )

        # GNN层
        for i, gnn_layer in enumerate(self.gnn_layers):
            h = gnn_layer(g, h)
            h = {k: F.relu(v) for k, v in h.items()}
            h = {k: self.dropout_layer(v) for k, v in h.items()}

        # 输出层
        embeddings = {}
        for ntype in self.node_types:
            embeddings[ntype] = self.output_layers[ntype](h[ntype])

        return embeddings

    def predict_root_cause(
        self, g: dgl.DGLHeteroGraph, features: Dict[str, torch.Tensor], alert_node_id: str
    ) -> Dict[str, Any]:
        """
        预测根因节点

        参数:
            g: 异构图
            features: 节点特征字典
            alert_node_id: 告警节点ID

        返回:
            根因预测结果
        """
        # 获取节点嵌入
        embeddings = self.forward(g, features)

        # 对所有节点进行分类
        root_cause_scores = {}
        for ntype, emb in embeddings.items():
            scores = self.classifier(emb)
            probs = F.softmax(scores, dim=1)
            root_cause_scores[ntype] = probs[:, 1].detach().cpu().numpy()  # 根因概率

        # 找到根因概率最高的节点
        max_score = 0.0
        root_cause_node = None
        root_cause_type = None

        for ntype, scores in root_cause_scores.items():
            for idx, score in enumerate(scores):
                if score > max_score:
                    max_score = score
                    root_cause_node = idx
                    root_cause_type = ntype

        return {
            "root_cause_node": root_cause_node,
            "root_cause_type": root_cause_type,
            "root_cause_score": float(max_score),
            "all_scores": root_cause_scores,
        }

    def compute_attention_weights(
        self, g: dgl.DGLHeteroGraph, features: Dict[str, torch.Tensor]
    ) -> Dict[str, np.ndarray]:
        """
        计算注意力权重（用于解释性）

        参数:
            g: 异构图
            features: 节点特征字典

        返回:
            注意力权重字典
        """
        embeddings = self.forward(g, features)

        # 简化的注意力计算（基于节点相似度）
        attention_weights = {}
        for ntype, emb in embeddings.items():
            # 计算节点间的余弦相似度
            emb_norm = F.normalize(emb, p=2, dim=1)
            attention = torch.mm(emb_norm, emb_norm.t())
            attention_weights[ntype] = attention.detach().cpu().numpy()

        return attention_weights

    def save_model(self, path: str) -> None:
        """保存模型"""
        torch.save(
            {
                "model_state_dict": self.state_dict(),
                "node_types": self.node_types,
                "edge_types": self.edge_types,
                "in_feats": self.in_feats,
                "hidden_feats": self.hidden_feats,
                "out_feats": self.out_feats,
                "num_layers": self.num_layers,
                "dropout": self.dropout,
            },
            path,
        )
        logger.info("GNN model saved to %s", path)

    def load_model(self, path: str) -> None:
        """加载模型"""
        checkpoint = torch.load(path)
        self.load_state_dict(checkpoint["model_state_dict"])
        self.node_types = checkpoint["node_types"]
        self.edge_types = checkpoint["edge_types"]
        self.in_feats = checkpoint["in_feats"]
        self.hidden_feats = checkpoint["hidden_feats"]
        self.out_feats = checkpoint["out_feats"]
        self.num_layers = checkpoint["num_layers"]
        self.dropout = checkpoint["dropout"]
        logger.info("GNN model loaded from %s", path)


class GNNTrainer:
    """
    GNN模型训练器

    负责训练异构图神经网络模型。
    """

    def __init__(
        self,
        model: HeterogeneousGNNModel,
        learning_rate: float = 0.001,
        weight_decay: float = 1e-5,
    ):
        self.model = model
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay

        self.optimizer = torch.optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )

        self.criterion = nn.CrossEntropyLoss()

    def train_epoch(
        self,
        g: dgl.DGLHeteroGraph,
        features: Dict[str, torch.Tensor],
        labels: Dict[str, torch.Tensor],
        mask: Optional[Dict[str, torch.Tensor]] = None,
    ) -> Dict[str, float]:
        """
        训练一个epoch

        参数:
            g: 异构图
            features: 节点特征
            labels: 节点标签
            mask: 训练掩码

        返回:
            训练指标
        """
        self.model.train()

        # 前向传播
        embeddings = self.model(g, features)

        # 计算损失
        total_loss = torch.tensor(0.0, device=next(self.model.parameters()).device)
        total_correct = 0
        total_samples = 0

        for ntype in self.model.node_types:
            if ntype in labels:
                pred = self.model.classifier(embeddings[ntype])

                if mask is not None and ntype in mask:
                    pred = pred[mask[ntype]]
                    label = labels[ntype][mask[ntype]]
                else:
                    label = labels[ntype]

                loss = self.criterion(pred, label)
                total_loss += loss

                # 计算准确率
                pred_labels = pred.argmax(dim=1)
                total_correct += (pred_labels == label).sum().item()
                total_samples += label.size(0)

        # 反向传播
        self.optimizer.zero_grad()
        total_loss.backward()
        self.optimizer.step()

        accuracy = total_correct / total_samples if total_samples > 0 else 0.0

        return {
            "loss": total_loss.item(),
            "accuracy": accuracy,
        }

    def evaluate(
        self,
        g: dgl.DGLHeteroGraph,
        features: Dict[str, torch.Tensor],
        labels: Dict[str, torch.Tensor],
        mask: Optional[Dict[str, torch.Tensor]] = None,
    ) -> Dict[str, float]:
        """
        评估模型

        参数:
            g: 异构图
            features: 节点特征
            labels: 节点标签
            mask: 评估掩码

        返回:
            评估指标
        """
        self.model.eval()

        with torch.no_grad():
            embeddings = self.model(g, features)

            total_loss = 0.0
            total_correct = 0
            total_samples = 0

            for ntype in self.model.node_types:
                if ntype in labels:
                    pred = self.model.classifier(embeddings[ntype])

                    if mask is not None and ntype in mask:
                        pred = pred[mask[ntype]]
                        label = labels[ntype][mask[ntype]]
                    else:
                        label = labels[ntype]

                    loss = self.criterion(pred, label)
                    total_loss += loss.item()

                    pred_labels = pred.argmax(dim=1)
                    total_correct += (pred_labels == label).sum().item()
                    total_samples += label.size(0)

            accuracy = total_correct / total_samples if total_samples > 0 else 0.0

        return {
            "loss": total_loss,
            "accuracy": accuracy,
        }
