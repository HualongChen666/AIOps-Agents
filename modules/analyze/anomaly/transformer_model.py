# -*- coding: utf-8 -*-
"""
transformer_model.py
--------------------
基于 Transformer 的时序异常检测模型。

支持多模态输入（指标 + 日志 + 追踪），实现深度学习异常检测。
目标：召回率 ≥ 98%，误报率 ≤ 2%

架构设计：
- Input Embedding: 将时序数据编码为向量
- Positional Encoding: 添加位置信息
- Transformer Encoder: 多层自注意力机制
- Anomaly Head: 异常检测输出层
- Multi-modal Fusion: 多模态特征融合
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple, cast  # noqa: F401

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 位置编码
# ----------------------------------------------------------------------
class PositionalEncoding(nn.Module):
    """Transformer 位置编码"""

    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer("pe", pe)
        self.pe: torch.Tensor

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, seq_len, d_model)"""
        return x + self.pe[:, : x.size(1)]


# ----------------------------------------------------------------------
# 2️⃣ 输入嵌入层
# ----------------------------------------------------------------------
class InputEmbedding(nn.Module):
    """时序数据嵌入层"""

    def __init__(self, input_dim: int, d_model: int, dropout: float = 0.1):
        super().__init__()
        self.linear = nn.Linear(input_dim, d_model)
        self.dropout = nn.Dropout(dropout)
        self.layer_norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, seq_len, input_dim)"""
        x = self.linear(x)
        x = self.layer_norm(x)
        x = self.dropout(x)
        return x


# ----------------------------------------------------------------------
# 3️⃣ Transformer 编码器
# ----------------------------------------------------------------------
class TransformerEncoderLayer(nn.Module):
    """自定义 Transformer 编码器层"""

    def __init__(self, d_model: int, n_heads: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.self_attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.feed_forward = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """x: (batch, seq_len, d_model)"""
        # Self-attention
        attn_output, _ = self.self_attn(x, x, x, attn_mask=mask)
        x = self.norm1(x + self.dropout(attn_output))

        # Feed-forward
        ff_output = self.feed_forward(x)
        x = self.norm2(x + ff_output)

        return x


# ----------------------------------------------------------------------
# 4️⃣ 异常检测头
# ----------------------------------------------------------------------
class AnomalyDetectionHead(nn.Module):
    """异常检测输出层"""

    def __init__(self, d_model: int, hidden_dim: int):
        super().__init__()
        self.fc1 = nn.Linear(d_model, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, 1)
        self.dropout = nn.Dropout(0.1)
        self.activation = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, seq_len, d_model) -> (batch, seq_len, 1)"""
        x = self.fc1(x)
        x = self.activation(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x


# ----------------------------------------------------------------------
# 5️⃣ 多模态融合层
# ----------------------------------------------------------------------
class MultiModalFusion(nn.Module):
    """多模态特征融合层"""

    def __init__(self, metric_dim: int, log_dim: int, trace_dim: int, d_model: int):
        super().__init__()
        self.metric_embedding = nn.Linear(metric_dim, d_model)
        self.log_embedding = nn.Linear(log_dim, d_model)
        self.trace_embedding = nn.Linear(trace_dim, d_model)
        self.fusion = nn.Linear(d_model * 3, d_model)
        self.layer_norm = nn.LayerNorm(d_model)

    def forward(
        self,
        metric: torch.Tensor,
        log: Optional[torch.Tensor] = None,
        trace: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        metric: (batch, seq_len, metric_dim)
        log: (batch, seq_len, log_dim) or None
        trace: (batch, seq_len, trace_dim) or None
        """
        metric_emb = self.metric_embedding(metric)

        features = [metric_emb]
        if log is not None:
            log_emb = self.log_embedding(log)
            features.append(log_emb)
        if trace is not None:
            trace_emb = self.trace_embedding(trace)
            features.append(trace_emb)

        # 如果只有单模态，直接返回
        if len(features) == 1:
            return cast(torch.Tensor, self.layer_norm(features[0]))

        # 多模态融合
        fused = torch.cat(features, dim=-1)
        fused = self.fusion(fused)
        return cast(torch.Tensor, self.layer_norm(fused))


# ----------------------------------------------------------------------
# 6️⃣ 完整的 Transformer 异常检测模型
# ----------------------------------------------------------------------
class TransformerAnomalyDetector(nn.Module):
    """基于 Transformer 的时序异常检测模型

    Parameters
    ----------
    input_dim : int
        输入特征维度
    d_model : int
        Transformer 模型维度
    n_heads : int
        注意力头数
    n_layers : int
        Transformer 层数
    d_ff : int
        前馈网络维度
    dropout : float
        Dropout 比例
    metric_dim : int
        指标特征维度
    log_dim : int
        日志特征维度（可选）
    trace_dim : int
        追踪特征维度（可选）
    """

    def __init__(
        self,
        input_dim: int = 1,
        d_model: int = 128,
        n_heads: int = 8,
        n_layers: int = 4,
        d_ff: int = 512,
        dropout: float = 0.1,
        metric_dim: int = 1,
        log_dim: int = 64,
        trace_dim: int = 64,
    ):
        super().__init__()
        # 参数验证
        if input_dim <= 0:
            raise ValueError(f"input_dim must be positive, got {input_dim}")
        if d_model <= 0:
            raise ValueError(f"d_model must be positive, got {d_model}")
        if n_heads <= 0:
            raise ValueError(f"n_heads must be positive, got {n_heads}")
        if d_model % n_heads != 0:
            raise ValueError(f"d_model ({d_model}) must be divisible by n_heads ({n_heads})")
        if n_layers <= 0:
            raise ValueError(f"n_layers must be positive, got {n_layers}")
        if not 0 <= dropout < 1:
            raise ValueError(f"dropout must be in [0, 1), got {dropout}")

        self.d_model = d_model
        self.input_dim = input_dim

        # 多模态融合
        self.multimodal_fusion = MultiModalFusion(metric_dim, log_dim, trace_dim, d_model)

        # 位置编码
        self.pos_encoding = PositionalEncoding(d_model)

        # Transformer 编码器
        self.transformer_layers = nn.ModuleList(
            [TransformerEncoderLayer(d_model, n_heads, d_ff, dropout) for _ in range(n_layers)]
        )

        # 异常检测头
        self.anomaly_head = AnomalyDetectionHead(d_model, hidden_dim=256)

        # 重构头（用于训练）
        self.reconstruction_head = nn.Linear(d_model, input_dim)

    def forward(
        self,
        metric: torch.Tensor,
        log: Optional[torch.Tensor] = None,
        trace: Optional[torch.Tensor] = None,
        mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播

        Returns
        -------
        anomaly_scores : torch.Tensor
            异常分数 (batch, seq_len, 1)
        reconstruction : torch.Tensor
            重构输出 (batch, seq_len, input_dim)
        """
        # 多模态融合
        x = self.multimodal_fusion(metric, log, trace)

        # 位置编码
        x = self.pos_encoding(x)

        # Transformer 编码器
        for layer in self.transformer_layers:
            x = layer(x, mask)

        # 异常检测
        anomaly_scores = self.anomaly_head(x)

        # 重构
        reconstruction = self.reconstruction_head(x)

        return anomaly_scores, reconstruction


# ----------------------------------------------------------------------
# 7️⃣ 时序数据集
# ----------------------------------------------------------------------
class TimeSeriesDataset(Dataset):
    """时序数据集"""

    def __init__(
        self,
        data: np.ndarray,
        seq_len: int = 100,
        stride: int = 1,
        labels: Optional[np.ndarray] = None,
    ):
        """
        Parameters
        ----------
        data : np.ndarray
            时序数据 (n_samples, n_features)
        seq_len : int
            序列长度
        stride : int
            滑动窗口步长
        labels : np.ndarray, optional
            异常标签 (n_samples,)
        """
        self.data = data
        self.seq_len = seq_len
        self.stride = stride
        self.labels = labels

        # 生成滑动窗口
        self.indices = []
        for i in range(0, len(data) - seq_len + 1, stride):
            self.indices.append(i)

        logger.info(f"Created dataset with {len(self.indices)} sequences")

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        start_idx = self.indices[idx]
        end_idx = start_idx + self.seq_len

        sequence = self.data[start_idx:end_idx]
        sequence_tensor: torch.Tensor = torch.FloatTensor(sequence)

        if self.labels is not None:
            label = self.labels[start_idx:end_idx]
            label_tensor: torch.Tensor = torch.FloatTensor(label)
            return sequence_tensor, label_tensor

        return sequence_tensor, None


# ----------------------------------------------------------------------
# 8️⃣ 损失函数
# ----------------------------------------------------------------------
class AnomalyLoss(nn.Module):
    """异常检测损失函数"""

    def __init__(
        self,
        reconstruction_weight: float = 1.0,
        anomaly_weight: float = 0.5,
        contrastive_weight: float = 0.1,
    ):
        super().__init__()
        self.reconstruction_weight = reconstruction_weight
        self.anomaly_weight = anomaly_weight
        self.contrastive_weight = contrastive_weight

    def forward(
        self,
        reconstruction: torch.Tensor,
        original: torch.Tensor,
        anomaly_scores: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        计算总损失

        Parameters
        ----------
        reconstruction : torch.Tensor
            重构输出
        original : torch.Tensor
            原始输入
        anomaly_scores : torch.Tensor
            异常分数
        labels : torch.Tensor, optional
            真实标签（如果有）
        """
        # 重构损失（MSE）
        reconstruction_loss = F.mse_loss(reconstruction, original)

        # 异常分数损失
        if labels is not None:
            # 监督学习：使用真实标签
            anomaly_loss = F.binary_cross_entropy_with_logits(anomaly_scores.squeeze(-1), labels)
        else:
            # 无监督学习：鼓励正常样本的低异常分数
            anomaly_loss = torch.mean(anomaly_scores**2)

        # 对比损失（增强特征表示）
        contrastive_loss = self._contrastive_loss(anomaly_scores)

        total_loss = (
            self.reconstruction_weight * reconstruction_loss
            + self.anomaly_weight * anomaly_loss
            + self.contrastive_weight * contrastive_loss
        )

        return total_loss

    def _contrastive_loss(self, anomaly_scores: torch.Tensor) -> torch.Tensor:
        """对比损失：拉近正常样本，推远异常样本"""
        # 简化版：使用方差作为对比损失
        return torch.var(anomaly_scores)


# ----------------------------------------------------------------------
# 9️⃣ 模型训练器
# ----------------------------------------------------------------------
class TransformerAnomalyTrainer:
    """Transformer 异常检测模型训练器"""

    def __init__(
        self,
        model: TransformerAnomalyDetector,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        learning_rate: float = 1e-4,
        weight_decay: float = 1e-5,
    ):
        self.model = model.to(device)
        self.device = device
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode="min",
            factor=0.5,
            patience=10,
        )
        self.criterion = AnomalyLoss()
        self.best_loss = float("inf")

    def train_epoch(
        self,
        train_loader: DataLoader,
        epoch: int,
    ) -> float:
        """训练一个 epoch"""
        self.model.train()
        total_loss = 0.0

        for batch_idx, (data, labels) in enumerate(train_loader):
            data = data.to(self.device)
            if labels is not None:
                labels = labels.to(self.device)

            self.optimizer.zero_grad()

            # 前向传播
            anomaly_scores, reconstruction = self.model(data)

            # 计算损失
            loss = self.criterion(reconstruction, data, anomaly_scores, labels)

            # 反向传播
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

            total_loss += loss.item()

            if batch_idx % 100 == 0:
                logger.info(f"Epoch {epoch}, Batch {batch_idx}, Loss: {loss.item():.4f}")

        avg_loss = total_loss / len(train_loader)
        return avg_loss

    def validate(
        self,
        val_loader: DataLoader,
    ) -> float:
        """验证"""
        self.model.eval()
        total_loss = 0.0

        with torch.no_grad():
            for data, labels in val_loader:
                data = data.to(self.device)
                if labels is not None:
                    labels = labels.to(self.device)

                anomaly_scores, reconstruction = self.model(data)
                loss = self.criterion(reconstruction, data, anomaly_scores, labels)
                total_loss += loss.item()

        avg_loss = total_loss / len(val_loader)
        return avg_loss

    def train(
        self,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        n_epochs: int = 100,
        patience: int = 20,
        model_path: str = "best_model.pth",
    ):
        """完整训练流程"""
        logger.info(f"Starting training for {n_epochs} epochs")

        no_improve = 0

        for epoch in range(n_epochs):
            # 训练
            train_loss = self.train_epoch(train_loader, epoch)
            logger.info(f"Epoch {epoch}, Train Loss: {train_loss:.4f}")

            # 验证
            if val_loader is not None:
                val_loss = self.validate(val_loader)
                logger.info(f"Epoch {epoch}, Val Loss: {val_loss:.4f}")
                self.scheduler.step(val_loss)

                # 保存最佳模型
                if val_loss < self.best_loss:
                    self.best_loss = val_loss
                    torch.save(self.model.state_dict(), model_path)
                    logger.info(f"Saved best model with val_loss: {val_loss:.4f}")
                    no_improve = 0
                else:
                    no_improve += 1
            else:
                self.scheduler.step(train_loss)
                if train_loss < self.best_loss:
                    self.best_loss = train_loss
                    torch.save(self.model.state_dict(), model_path)
                    logger.info(f"Saved best model with train_loss: {train_loss:.4f}")
                    no_improve = 0
                else:
                    no_improve += 1

            # Early stopping
            if no_improve >= patience:
                logger.info(f"Early stopping at epoch {epoch}")
                break

        logger.info("Training completed")

    def load_model(self, model_path: str):
        """加载模型"""
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        logger.info(f"Loaded model from {model_path}")


# ----------------------------------------------------------------------
# 🔟 推理接口
# ----------------------------------------------------------------------
class TransformerAnomalyDetectorWrapper:
    """异常检测推理接口"""

    def __init__(
        self,
        model: TransformerAnomalyDetector,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        threshold: float = 0.5,
    ):
        self.model = model.to(device)
        self.model.eval()
        self.device = device
        self.threshold = threshold

    def detect(
        self,
        data: np.ndarray,
        log_data: Optional[np.ndarray] = None,
        trace_data: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        检测异常

        Parameters
        ----------
        data : np.ndarray
            指标数据 (n_samples, n_features)
        log_data : np.ndarray, optional
            日志特征 (n_samples, log_dim)
        trace_data : np.ndarray, optional
            追踪特征 (n_samples, trace_dim)

        Returns
        -------
        is_anomaly : np.ndarray
            异常标记 (n_samples,)
        anomaly_scores : np.ndarray
            异常分数 (n_samples,)
        """
        with torch.no_grad():
            # 转换为 tensor
            metric_tensor = (
                torch.FloatTensor(data).unsqueeze(0).to(self.device)
            )  # (1, seq_len, features)

            log_tensor = None
            if log_data is not None:
                log_tensor = torch.FloatTensor(log_data).unsqueeze(0).to(self.device)

            trace_tensor = None
            if trace_data is not None:
                trace_tensor = torch.FloatTensor(trace_data).unsqueeze(0).to(self.device)

            # 前向传播
            anomaly_scores, _ = self.model(metric_tensor, log_tensor, trace_tensor)

            # 转换为 numpy
            anomaly_scores = anomaly_scores.squeeze(0).squeeze(-1).cpu().numpy()

            # 应用阈值
            is_anomaly = anomaly_scores > self.threshold

        return is_anomaly, anomaly_scores


# ----------------------------------------------------------------------
# 1️⃣1️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_transformer_model(
    input_dim: int = 1,
    d_model: int = 128,
    n_heads: int = 8,
    n_layers: int = 4,
    d_ff: int = 512,
    dropout: float = 0.1,
) -> TransformerAnomalyDetector:
    """创建 Transformer 异常检测模型"""
    model = TransformerAnomalyDetector(
        input_dim=input_dim,
        d_model=d_model,
        n_heads=n_heads,
        n_layers=n_layers,
        d_ff=d_ff,
        dropout=dropout,
    )
    return model


# ----------------------------------------------------------------------
# 1️⃣2️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    # 简单测试
    logger.info("Testing Transformer Anomaly Detector")

    # 创建模型
    model = create_transformer_model(input_dim=1, d_model=64, n_heads=4, n_layers=2)
    logger.info(f"Model created with {sum(p.numel() for p in model.parameters())} parameters")

    # 测试前向传播
    batch_size = 4
    seq_len = 100
    input_dim = 1

    metric = torch.randn(batch_size, seq_len, input_dim)
    anomaly_scores, reconstruction = model(metric)

    logger.info(f"Anomaly scores shape: {anomaly_scores.shape}")
    logger.info(f"Reconstruction shape: {reconstruction.shape}")

    logger.info("Test passed!")
