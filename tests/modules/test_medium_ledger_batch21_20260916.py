# -*- coding: utf-8 -*-
"""中危台账批次 21 回归测试（modules/，2026-09-16）。

覆盖条目：
- M-007 modules/analyze/anomaly/transformer_model.py     detect 对 raw logits 应用 sigmoid（阈值 0.5 语义正确）
- M-014 modules/analyze/root_cause/causal_graph_builder.py 按 discovery_method 真实分派 pc / ges
- M-021 modules/analyze/runbook/generator.py             无 LLM 客户端不再伪造输出（如实失败）
- M-023 modules/analyze/runbook/vector_store.py          无嵌入模型时不再返回随机向量（如实失败）
- M-008 modules/analyze/anomaly/transformer_service.py   不再用硬编码 "2024-01-01" 伪造时间戳；路由强制鉴权
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# M-007 — sigmoid applied to logits
# ---------------------------------------------------------------------------
def _build_model_with_constant_logit(bias: float):
    import torch

    from modules.analyze.anomaly.transformer_model import create_transformer_model

    model = create_transformer_model(input_dim=1, d_model=16, n_heads=2, n_layers=1, d_ff=32)
    with torch.no_grad():
        for p in model.parameters():
            p.data.zero_()
        # 让异常头输出恒定 logits=bias（fc2 的偏置）
        model.anomaly_head.fc2.bias.data.fill_(bias)
    model.eval()
    return model


def test_transformer_detect_applies_sigmoid():
    import torch

    from modules.analyze.anomaly.transformer_model import TransformerAnomalyDetectorWrapper

    data = np.random.rand(10, 1).astype(np.float32)

    high = TransformerAnomalyDetectorWrapper(_build_model_with_constant_logit(10.0), threshold=0.5)
    is_anomaly, scores = high.detect(data)
    assert scores.min() >= 0.0 and scores.max() <= 1.0  # sigmoid → 概率区间
    assert scores.max() > 0.99
    assert bool(is_anomaly.all())

    low = TransformerAnomalyDetectorWrapper(_build_model_with_constant_logit(-10.0), threshold=0.5)
    is_anomaly2, scores2 = low.detect(data)
    assert scores2.min() >= 0.0 and scores2.max() <= 1.0
    assert scores2.max() < 0.01
    assert not bool(is_anomaly2.any())


# ---------------------------------------------------------------------------
# M-014 — discovery_method dispatch
# ---------------------------------------------------------------------------
def test_causal_builder_honours_discovery_method(monkeypatch):
    import pandas as pd

    import modules.analyze.root_cause.causal_graph_builder as cgb

    called: List[str] = []
    orig_pc = cgb.CausalDiscovery.pc_algorithm
    orig_ges = cgb.CausalDiscovery.ges_algorithm

    def spy_pc(data, **kw):
        called.append("pc")
        return orig_pc(data, **kw)

    def spy_ges(data, **kw):
        called.append("ges")
        return orig_ges(data, **kw)

    monkeypatch.setattr(cgb.CausalDiscovery, "pc_algorithm", staticmethod(spy_pc))
    monkeypatch.setattr(cgb.CausalDiscovery, "ges_algorithm", staticmethod(spy_ges))

    rng = np.random.default_rng(0)
    a = rng.normal(size=60)
    b = a + rng.normal(scale=0.1, size=60)
    c = b + rng.normal(scale=0.1, size=60)
    df = pd.DataFrame({"a": a, "b": b, "c": c})

    cgb.CausalGraphBuilder(discovery_method="ges").build_from_metrics(df)
    assert called == ["ges"]
    called.clear()

    cgb.CausalGraphBuilder(discovery_method="pc").build_from_metrics(df)
    assert called == ["pc"]


# ---------------------------------------------------------------------------
# M-021 — no fabricated LLM output
# ---------------------------------------------------------------------------
class _FakeVectorStore:
    def __init__(self) -> None:
        self.is_initialized = False

    def initialize(self) -> None:
        self.is_initialized = True

    def search(self, *a, **k):
        return []


def test_runbook_generator_fails_honestly_without_llm():
    from modules.analyze.runbook.generator import RunbookGenerator

    gen = RunbookGenerator(vector_store=_FakeVectorStore(), llm_provider="local")
    with pytest.raises(RuntimeError):
        gen._call_llm("prompt")

    result = gen.generate_runbook({"title": "boom"}, use_rag=False)
    assert result["success"] is False
    assert result["fallback"] is True
    assert "error" in result


# ---------------------------------------------------------------------------
# M-023 — no random embeddings
# ---------------------------------------------------------------------------
def test_vector_store_embed_fails_without_model():
    from modules.analyze.runbook.vector_store import VectorStore

    vs = VectorStore()
    assert vs.embedding_model is None
    with pytest.raises(RuntimeError):
        vs.embed_text("hello")
    with pytest.raises(RuntimeError):
        vs.embed_batch(["hello", "world"])


# ---------------------------------------------------------------------------
# M-008 — real timestamps + auth on router
# ---------------------------------------------------------------------------
class _RecordingPreprocessor:
    def __init__(self) -> None:
        self.seen_df = None

    def process(self, df, timestamp_col, value_col):
        self.seen_df = df
        return np.random.rand(len(df), 1).astype(np.float32)


class _FakeWrapper:
    def detect(self, processed, *a, **k):
        return np.array([False]), np.array([0.1])


class _FakeManager:
    def __init__(self):
        self.is_loaded = True
        self.preprocessor = _RecordingPreprocessor()
        self.wrapper = _FakeWrapper()


def test_detect_single_uses_real_timestamps():
    from modules.analyze.anomaly.transformer_service import TransformerAnomalyService

    manager = _FakeManager()
    service = TransformerAnomalyService(manager)

    # 未提供时间戳：应以当前时间为锚点，而非硬编码 2024-01-01
    service.detect_single([1.0, 2.0, 3.0])
    ts = manager.preprocessor.seen_df["timestamp"]
    assert str(ts.iloc[0])[:4] != "2024"
    assert ts.iloc[0] < ts.iloc[-1]

    # 提供真实时间戳：应被采用
    provided = ["2025-05-01T00:00:00", "2025-05-01T00:01:00", "2025-05-01T00:02:00"]
    service.detect_single([1.0, 2.0, 3.0], timestamps=provided)
    ts2 = manager.preprocessor.seen_df["timestamp"]
    assert str(ts2.iloc[0]).startswith("2025-05-01")

    # 长度不匹配 → 400
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        service.detect_single([1.0, 2.0], timestamps=["2025-05-01T00:00:00"])
    assert exc.value.status_code == 400


def test_transformer_router_requires_auth():
    from modules.analyze.anomaly.transformer_service import create_router

    router = create_router()
    # 路由级依赖非空（鉴权）
    assert router.dependencies
