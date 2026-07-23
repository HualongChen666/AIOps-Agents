# -*- coding: utf-8 -*-
"""
train_transformer.py
--------------------
Transformer 异常检测模型训练脚本。

功能：
- 数据加载和预处理
- 模型训练
- 模型验证
- 模型保存和加载
- 性能评估
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, cast  # noqa: F401

import numpy as np
import torch
from torch.utils.data import DataLoader

from .data_preprocessing import (
    TimeSeriesDataLoader,
    TimeSeriesPreprocessingPipeline,
    TimeSeriesSplitter,
)
from .transformer_model import (
    TimeSeriesDataset,
    TransformerAnomalyDetector,
    TransformerAnomalyTrainer,
    create_transformer_model,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 配置
# ----------------------------------------------------------------------
class TrainingConfig:
    """训练配置"""

    def __init__(
        self,
        # 数据配置
        data_path: str = "data/timeseries.csv",
        timestamp_col: str = "timestamp",
        value_col: str = "value",
        seq_len: int = 100,
        stride: int = 1,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        # 模型配置
        input_dim: int = 1,
        d_model: int = 128,
        n_heads: int = 8,
        n_layers: int = 4,
        d_ff: int = 512,
        dropout: float = 0.1,
        # 训练配置
        batch_size: int = 32,
        n_epochs: int = 100,
        learning_rate: float = 1e-4,
        weight_decay: float = 1e-5,
        patience: int = 20,
        # 输出配置
        model_dir: str = "models/anomaly",
        model_name: str = "transformer_anomaly_detector.pth",
        # 其他
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        seed: int = 42,
    ):
        self.data_path = data_path
        self.timestamp_col = timestamp_col
        self.value_col = value_col
        self.seq_len = seq_len
        self.stride = stride
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio

        self.input_dim = input_dim
        self.d_model = d_model
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.d_ff = d_ff
        self.dropout = dropout

        self.batch_size = batch_size
        self.n_epochs = n_epochs
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.patience = patience

        self.model_dir = model_dir
        self.model_name = model_name

        self.device = device
        self.seed = seed


# ----------------------------------------------------------------------
# 2️⃣ 数据准备
# ----------------------------------------------------------------------
def prepare_data(
    config: TrainingConfig,
) -> tuple:
    """
    准备训练数据

    Returns
    -------
    train_loader : DataLoader
        训练数据加载器
    val_loader : DataLoader
        验证数据加载器
    test_loader : DataLoader
        测试数据加载器
    input_dim : int
        输入维度
    """
    logger.info("Preparing data...")

    # 加载数据
    if config.data_path.endswith(".csv"):
        df = TimeSeriesDataLoader.load_from_csv(
            config.data_path,
            config.timestamp_col,
            config.value_col,
        )
    else:
        raise ValueError(f"Unsupported data format: {config.data_path}")

    # 预处理
    pipeline = TimeSeriesPreprocessingPipeline(
        clean_missing=True,
        clean_outliers=False,
        add_features=True,
        scale=True,
        scale_method="standard",
        augment=False,
    )

    processed_data = pipeline.process(
        df,
        config.timestamp_col,
        config.value_col,
    )

    # 更新输入维度
    input_dim = processed_data.shape[1]
    logger.info(f"Input dimension: {input_dim}")

    # 划分数据集
    train_data, val_data, test_data, _, _, _ = TimeSeriesSplitter.train_val_test_split(
        processed_data,
        train_ratio=config.train_ratio,
        val_ratio=config.val_ratio,
        test_ratio=config.test_ratio,
        shuffle=False,
    )

    # 创建数据集
    train_dataset = TimeSeriesDataset(
        train_data,
        seq_len=config.seq_len,
        stride=config.stride,
    )
    val_dataset = TimeSeriesDataset(
        val_data,
        seq_len=config.seq_len,
        stride=config.stride,
    )
    test_dataset = TimeSeriesDataset(
        test_data,
        seq_len=config.seq_len,
        stride=config.stride,
    )

    # 创建数据加载器
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=0,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=0,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=0,
    )

    logger.info(
        f"Data prepared: train={len(train_dataset)}, "
        f"val={len(val_dataset)}, test={len(test_dataset)}"
    )

    return train_loader, val_loader, test_loader, input_dim


# ----------------------------------------------------------------------
# 3️⃣ 模型训练
# ----------------------------------------------------------------------
def train_model(
    config: TrainingConfig,
    train_loader: DataLoader,
    val_loader: DataLoader,
    input_dim: int,
) -> TransformerAnomalyDetector:
    """
    训练模型

    Returns
    -------
    model : TransformerAnomalyDetector
        训练好的模型
    """
    logger.info("Creating model...")

    # 创建模型
    model = create_transformer_model(
        input_dim=input_dim,
        d_model=config.d_model,
        n_heads=config.n_heads,
        n_layers=config.n_layers,
        d_ff=config.d_ff,
        dropout=config.dropout,
    )

    logger.info(f"Model created with {sum(p.numel() for p in model.parameters())} parameters")

    # 创建训练器
    trainer = TransformerAnomalyTrainer(
        model=model,
        device=config.device,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    # 创建模型目录
    model_dir = Path(config.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / config.model_name

    # 训练
    trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        n_epochs=config.n_epochs,
        patience=config.patience,
        model_path=str(model_path),
    )

    # 加载最佳模型
    trainer.load_model(str(model_path))

    return model


# ----------------------------------------------------------------------
# 4️⃣ 模型评估
# ----------------------------------------------------------------------
def evaluate_model(
    model: TransformerAnomalyDetector,
    test_loader: DataLoader,
    config: TrainingConfig,
) -> Dict[str, float]:
    """
    评估模型

    Returns
    -------
    metrics : Dict[str, float]
        评估指标
    """
    logger.info("Evaluating model...")

    all_scores_list: List[np.ndarray] = []
    all_reconstructions_list: List[np.ndarray] = []
    all_originals_list: List[np.ndarray] = []

    model.eval()
    with torch.no_grad():
        for data, _ in test_loader:
            data = data.to(config.device)

            # 前向传播
            anomaly_scores, reconstruction = model(data)

            all_scores_list.append(anomaly_scores.cpu().numpy())
            all_reconstructions_list.append(reconstruction.cpu().numpy())
            all_originals_list.append(data.cpu().numpy())

    # 计算指标
    all_scores = np.concatenate(all_scores_list)
    all_reconstructions = np.concatenate(all_reconstructions_list)
    all_originals = np.concatenate(all_originals_list)

    # 重构误差
    reconstruction_error = np.mean((all_originals - all_reconstructions) ** 2)

    # 异常分数统计
    anomaly_mean = np.mean(all_scores)
    anomaly_std = np.std(all_scores)

    metrics = {
        "reconstruction_error": float(reconstruction_error),
        "anomaly_score_mean": float(anomaly_mean),
        "anomaly_score_std": float(anomaly_std),
    }

    logger.info(f"Evaluation metrics: {metrics}")
    return metrics


# ----------------------------------------------------------------------
# 5️⃣ 主函数
# ----------------------------------------------------------------------
def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Train Transformer Anomaly Detector")
    parser.add_argument(
        "--data_path", type=str, default="data/timeseries.csv", help="Path to training data"
    )
    parser.add_argument("--model_dir", type=str, default="models/anomaly", help="Model directory")
    parser.add_argument("--epochs", type=int, default=100, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--device", type=str, default="cuda", help="Device to use")

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 创建配置
    config = TrainingConfig(
        data_path=args.data_path,
        model_dir=args.model_dir,
        n_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        device=args.device,
    )

    # 设置随机种子
    torch.manual_seed(config.seed)
    np.random.seed(config.seed)

    logger.info("Starting training pipeline")
    logger.info(f"Configuration: {vars(config)}")

    # 准备数据
    train_loader, val_loader, test_loader, input_dim = prepare_data(config)

    # 训练模型
    model = train_model(config, train_loader, val_loader, input_dim)

    # 评估模型
    metrics = evaluate_model(model, test_loader, config)

    logger.info("Training pipeline completed successfully")
    logger.info(f"Final metrics: {metrics}")


if __name__ == "__main__":  # pragma: no cover
    main()
