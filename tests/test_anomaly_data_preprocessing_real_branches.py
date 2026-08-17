# -*- coding: utf-8 -*-
"""Real-branch coverage tests for modules.analyze.anomaly.data_preprocessing.

Uses real data and real library calls; no mocks or monkeypatching.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from modules.analyze.anomaly.data_preprocessing import (
    MultiModalDataPreparer,
    TimeSeriesAugmenter,
    TimeSeriesCleaner,
    TimeSeriesDataLoader,
    TimeSeriesFeatureEngineer,
    TimeSeriesPreprocessingPipeline,
    TimeSeriesScaler,
    TimeSeriesSplitter,
    create_preprocessing_pipeline,
)


def _sample_df(n: int = 30) -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01", periods=n, freq="1min")
    values = np.random.randn(n).cumsum() + 100.0
    return pd.DataFrame({"timestamp": timestamps, "value": values})


def _make_csv(path: Path, columns: list, rows: list) -> str:
    df = pd.DataFrame(rows, columns=columns)
    csv_path = path / "data.csv"
    df.to_csv(csv_path, index=False)
    return str(csv_path)


# ----------------------------------------------------------------------
# Data loader
# ----------------------------------------------------------------------


def test_load_from_csv_basic_and_additional_cols(tmp_path: Path) -> None:
    rows = [
        ["2024-01-01 00:00:00", 1.0, 10.0],
        ["2024-01-01 00:01:00", 2.0, 20.0],
    ]
    filepath = _make_csv(tmp_path, ["timestamp", "value", "extra"], rows)
    df = TimeSeriesDataLoader.load_from_csv(filepath, additional_cols=["extra"])
    assert "extra" in df.columns
    assert len(df) == 2


def test_load_from_csv_missing_timestamp_raises(tmp_path: Path) -> None:
    filepath = _make_csv(tmp_path, ["ts", "value"], [["2024-01-01", 1.0]])
    with pytest.raises(ValueError):
        TimeSeriesDataLoader.load_from_csv(filepath)


def test_load_from_database_invalid_query_raises() -> None:
    with pytest.raises(ValueError):
        TimeSeriesDataLoader.load_from_database("", {})


def test_load_from_database_missing_connection_param_raises() -> None:
    with pytest.raises(ValueError):
        TimeSeriesDataLoader.load_from_database("SELECT 1", {"password": "x"})


def test_load_from_database_valid_params_eventually_raises() -> None:
    """All required params are supplied; the function reaches the engine/connection code."""
    params = {
        "user": "u",
        "password": "p",
        "host": "127.0.0.1",
        "port": 1,
        "database": "db",
    }
    with pytest.raises(Exception):
        TimeSeriesDataLoader.load_from_database("SELECT 1", params)


# ----------------------------------------------------------------------
# Data cleaner
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,expected",
    [
        ("ffill", pd.Series([1.0, 1.0, 3.0])),
        ("bfill", pd.Series([1.0, 3.0, 3.0])),
        ("zero", pd.Series([1.0, 0.0, 3.0])),
    ],
)
def test_handle_missing_values_methods(method: str, expected: pd.Series) -> None:
    df = pd.DataFrame({"value": [1.0, np.nan, 3.0]})
    result = TimeSeriesCleaner.handle_missing_values(df, method=method)
    pd.testing.assert_series_equal(
        result["value"].reset_index(drop=True), expected, check_names=False
    )


def test_handle_missing_values_interpolate() -> None:
    df = pd.DataFrame({"value": [1.0, np.nan, 3.0, np.nan, 5.0]})
    result = TimeSeriesCleaner.handle_missing_values(df, method="interpolate")
    assert result["value"].notna().all()


def test_handle_missing_values_drop() -> None:
    df = pd.DataFrame({"value": [1.0, np.nan, 3.0]})
    result = TimeSeriesCleaner.handle_missing_values(df, method="drop")
    assert len(result) == 2


def test_handle_missing_values_unknown_method_raises() -> None:
    df = pd.DataFrame({"value": [1.0, np.nan, 3.0]})
    with pytest.raises(ValueError):
        TimeSeriesCleaner.handle_missing_values(df, method="unknown")


def test_remove_outliers_iqr_removes_outliers() -> None:
    df = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0, 100.0]})
    result = TimeSeriesCleaner.remove_outliers(df, method="iqr", threshold=1.5)
    assert len(result) < len(df)


def test_remove_outliers_zscore() -> None:
    df = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})
    result = TimeSeriesCleaner.remove_outliers(df, method="zscore", threshold=2.0)
    assert len(result) < len(df)


def test_remove_outliers_isolation() -> None:
    df = pd.DataFrame({"value": list(range(20)) + [999.0]})
    result = TimeSeriesCleaner.remove_outliers(df, method="isolation")
    assert len(result) <= len(df)


def test_remove_outliers_no_outliers() -> None:
    df = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0, 5.0]})
    result = TimeSeriesCleaner.remove_outliers(df, method="zscore", threshold=5.0)
    assert len(result) == len(df)


def test_remove_outliers_unknown_method_raises() -> None:
    df = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError):
        TimeSeriesCleaner.remove_outliers(df, method="unknown")


@pytest.mark.parametrize("agg", ["mean", "sum", "max", "min", "median"])
def test_resample_aggregations(agg: str) -> None:
    n = 10
    timestamps = pd.date_range("2024-01-01", periods=n, freq="1min")
    df = pd.DataFrame({"timestamp": timestamps, "value": np.arange(n, dtype=float)})
    result = TimeSeriesCleaner.resample(df, freq="5min", agg=agg)
    assert isinstance(result, pd.DataFrame)
    assert "timestamp" in result.columns and "value" in result.columns
    assert len(result) > 0


def test_resample_unknown_aggregation_raises() -> None:
    df = _sample_df(10)
    with pytest.raises(ValueError):
        TimeSeriesCleaner.resample(df, freq="5min", agg="unknown")


# ----------------------------------------------------------------------
# Feature engineering
# ----------------------------------------------------------------------


def test_add_lag_features() -> None:
    df = _sample_df(10)
    result = TimeSeriesFeatureEngineer.add_lag_features(df, lags=[1, 3])
    assert "value_lag_1" in result.columns
    assert "value_lag_3" in result.columns
    assert len(result) == len(df)


def test_add_rolling_features() -> None:
    df = _sample_df(10)
    result = TimeSeriesFeatureEngineer.add_rolling_features(df, windows=[3])
    assert "value_rolling_mean_3" in result.columns
    assert "value_rolling_std_3" in result.columns
    assert len(result) == len(df)


def test_add_time_features() -> None:
    df = _sample_df(10)
    result = TimeSeriesFeatureEngineer.add_time_features(df)
    for col in [
        "hour",
        "day_of_week",
        "day_of_month",
        "month",
        "is_weekend",
        "hour_sin",
        "hour_cos",
    ]:
        assert col in result.columns


def test_add_statistical_features() -> None:
    df = _sample_df(20)
    result = TimeSeriesFeatureEngineer.add_statistical_features(df, window=5)
    assert f"value_zscore" in result.columns
    assert f"value_pct_change" in result.columns
    assert f"value_diff" in result.columns


# ----------------------------------------------------------------------
# Augmenter
# ----------------------------------------------------------------------


def test_add_noise() -> None:
    data = np.random.randn(20, 3)
    result = TimeSeriesAugmenter.add_noise(data, noise_level=0.1)
    assert result.shape == data.shape


def test_time_warp() -> None:
    data = np.random.randn(20, 3)
    result = TimeSeriesAugmenter.time_warp(data, sigma=0.2)
    assert result.shape == data.shape


def test_magnitude_warp() -> None:
    data = np.random.randn(20, 3)
    result = TimeSeriesAugmenter.magnitude_warp(data, sigma=0.2)
    assert result.shape == data.shape


def test_augment_dataset_all_methods_and_labels() -> None:
    np.random.seed(0)
    data = np.random.randn(10, 3)
    labels = np.arange(10)
    augmented_data, augmented_labels = TimeSeriesAugmenter.augment_dataset(
        data, labels, augment_factor=100
    )
    assert augmented_data.shape[0] > data.shape[0]
    assert augmented_labels is not None
    assert augmented_labels.shape[0] == augmented_data.shape[0]


# ----------------------------------------------------------------------
# Scaler
# ----------------------------------------------------------------------


def test_scaler_2d_standard() -> None:
    data = np.random.randn(100, 4)
    scaler = TimeSeriesScaler(method="standard")
    scaled = scaler.fit_transform(data)
    assert scaled.shape == data.shape
    inv = scaler.inverse_transform(scaled)
    np.testing.assert_allclose(inv, data, atol=1e-5)


def test_scaler_2d_minmax() -> None:
    data = np.random.randn(100, 4)
    scaler = TimeSeriesScaler(method="minmax")
    scaled = scaler.fit_transform(data)
    assert scaled.shape == data.shape


def test_scaler_3d() -> None:
    data = np.random.randn(10, 5, 3)
    scaler = TimeSeriesScaler(method="standard")
    scaled = scaler.fit_transform(data)
    assert scaled.shape == data.shape
    inv = scaler.inverse_transform(scaled)
    np.testing.assert_allclose(inv, data, atol=1e-5)


def test_scaler_unknown_method_raises() -> None:
    with pytest.raises(ValueError):
        TimeSeriesScaler(method="unknown")


# ----------------------------------------------------------------------
# Splitter
# ----------------------------------------------------------------------


def test_train_val_test_split_no_labels() -> None:
    data = np.arange(100)
    train, val, test, train_l, val_l, test_l = TimeSeriesSplitter.train_val_test_split(
        data, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15
    )
    assert len(train) == 70
    assert len(val) == 15
    assert len(test) == 15
    assert train_l is None


def test_train_val_test_split_with_labels_and_shuffle() -> None:
    data = np.arange(100)
    labels = np.arange(100)
    train, val, test, train_l, val_l, test_l = TimeSeriesSplitter.train_val_test_split(
        data, labels, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, shuffle=True
    )
    assert len(train) == 70
    assert train_l is not None
    assert len(train_l) == len(train)


# ----------------------------------------------------------------------
# Pipeline
# ----------------------------------------------------------------------


def test_preprocessing_pipeline_all_defaults() -> None:
    df = _sample_df(50)
    pipeline = TimeSeriesPreprocessingPipeline()
    result = pipeline.process(df)
    assert isinstance(result, np.ndarray)
    assert result.shape[0] == len(df)


def test_preprocessing_pipeline_toggles() -> None:
    df = _sample_df(50)
    # Include an obvious outlier for the outlier cleaner.
    df.loc[df.index[-1], "value"] = 1e9
    pipeline = TimeSeriesPreprocessingPipeline(
        clean_missing=True,
        clean_outliers=True,
        add_features=True,
        scale=False,
    )
    result = pipeline.process(df, feature_cols=["value"])
    assert isinstance(result, np.ndarray)
    assert result.shape[1] == 1


def test_process_for_training_augment() -> None:
    np.random.seed(1)
    df = _sample_df(30)
    labels = np.arange(len(df))
    pipeline = TimeSeriesPreprocessingPipeline(augment=True, augment_factor=20)
    data, lbl = pipeline.process_for_training(df, labels)
    assert data.shape[0] > len(df)
    assert lbl is not None
    assert lbl.shape[0] == data.shape[0]


def test_create_preprocessing_pipeline() -> None:
    pipeline = create_preprocessing_pipeline(scale_method="minmax", add_features=False)
    df = _sample_df(20)
    result = pipeline.process(df)
    assert isinstance(result, np.ndarray)
    assert result.shape[0] == len(df)


# ----------------------------------------------------------------------
# Multi-modal data preparer
# ----------------------------------------------------------------------


def test_prepare_log_features_default_vectorizer() -> None:
    logs = ["error connection refused", "timeout", "success", "timeout connection"]
    features = MultiModalDataPreparer.prepare_log_features(logs)
    assert isinstance(features, np.ndarray)
    assert features.shape[0] == len(logs)


def test_prepare_trace_features() -> None:
    traces = [
        {"duration": 100, "spans": [{"error": False}, {"error": True}]},
        {"duration": 50, "spans": [{"error": False}]},
    ]
    features = MultiModalDataPreparer.prepare_trace_features(traces, feature_dim=16)
    assert features.shape == (2, 16)


# ----------------------------------------------------------------------
# Extra branch-side coverage
# ----------------------------------------------------------------------


def test_load_from_csv_without_additional_cols(tmp_path: Path) -> None:
    rows = [
        ["2024-01-01 00:00:00", 1.0],
        ["2024-01-01 00:01:00", 2.0],
    ]
    filepath = _make_csv(tmp_path, ["timestamp", "value"], rows)
    df = TimeSeriesDataLoader.load_from_csv(filepath)
    assert list(df.columns) == ["timestamp", "value"]


def test_augment_dataset_without_labels() -> None:
    np.random.seed(2)
    data = np.random.randn(10, 3)
    augmented_data, labels = TimeSeriesAugmenter.augment_dataset(
        data, labels=None, augment_factor=10
    )
    assert augmented_data.shape[0] > data.shape[0]
    assert labels is None


def test_train_val_test_split_shuffle_no_labels() -> None:
    data = np.arange(100)
    train, val, test, train_l, val_l, test_l = TimeSeriesSplitter.train_val_test_split(
        data, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, shuffle=True
    )
    assert len(train) == 70
    assert train_l is None


def test_preprocessing_pipeline_clean_missing_false() -> None:
    df = _sample_df(20)
    # Introduce a missing value but disable missing-value cleaning.
    df.loc[df.index[5], "value"] = np.nan
    pipeline = TimeSeriesPreprocessingPipeline(clean_missing=False)
    result = pipeline.process(df)
    assert result.shape[0] == len(df)


def test_process_for_training_no_augment() -> None:
    df = _sample_df(20)
    pipeline = TimeSeriesPreprocessingPipeline(augment=False)
    data, labels = pipeline.process_for_training(df)
    assert data.shape[0] == len(df)
    assert labels is None
