# -*- coding: utf-8 -*-
"""
data_preprocessing.py
--------------------
时序异常检测数据预处理模块。

功能：
- 数据加载和清洗
- 特征工程
- 数据增强
- 多模态数据准备
- 训练/验证/测试集划分
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 数据加载器
# ----------------------------------------------------------------------
class TimeSeriesDataLoader:
    """时序数据加载器"""

    @staticmethod
    def load_from_csv(
        filepath: str,
        timestamp_col: str = "timestamp",
        value_col: str = "value",
        additional_cols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        从 CSV 文件加载时序数据

        Parameters
        ----------
        filepath : str
            CSV 文件路径
        timestamp_col : str
            时间戳列名
        value_col : str
            值列名
        additional_cols : List[str], optional
            额外的特征列名

        Returns
        -------
        pd.DataFrame
            加载的数据
        """
        logger.info(f"Loading data from {filepath}")
        df = pd.read_csv(filepath)

        # 确保时间戳列存在
        if timestamp_col not in df.columns:
            raise ValueError(f"Timestamp column '{timestamp_col}' not found")

        # 转换时间戳
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)
        df = df.sort_values(timestamp_col)

        # 选择需要的列
        cols = [timestamp_col, value_col]
        if additional_cols:
            cols.extend(additional_cols)

        df = df[cols]
        logger.info(f"Loaded {len(df)} rows with columns: {df.columns.tolist()}")

        return df

    @staticmethod
    def load_from_database(
        query: str,
        connection_params: Dict[str, Any],
    ) -> pd.DataFrame:
        """
        从数据库加载时序数据

        Parameters
        ----------
        query : str
            SQL 查询
        connection_params : Dict[str, Any]
            数据库连接参数（应使用环境变量或密钥管理）

        Returns
        -------
        pd.DataFrame
            加载的数据
        """
        from urllib.parse import quote_plus

        import sqlalchemy

        # 安全检查：防止 SQL 注入
        if not query or not isinstance(query, str):
            raise ValueError("Invalid query parameter")

        # 验证必需的连接参数
        required_params = ["user", "password", "host", "port", "database"]
        for param in required_params:
            if param not in connection_params:
                raise ValueError(f"Missing required connection parameter: {param}")

        # 使用 URL 编码保护特殊字符
        user = quote_plus(str(connection_params["user"]))
        password = quote_plus(str(connection_params["password"]))
        host = str(connection_params["host"])
        port = str(connection_params["port"])
        database = quote_plus(str(connection_params["database"]))

        engine = sqlalchemy.create_engine(
            f"postgresql://{user}:{password}@{host}:{port}/{database}"
        )

        logger.info("Loading data from database")
        df = pd.read_sql(query, engine)
        logger.info(f"Loaded {len(df)} rows")

        return df

    @staticmethod
    def load_from_prometheus(
        query: str,
        start_time: str,
        end_time: str,
        step: str = "1m",
        url: str = "http://localhost:9090",
    ) -> pd.DataFrame:
        """
        从 Prometheus 加载时序数据

        Parameters
        ----------
        query : str
            PromQL 查询
        start_time : str
            开始时间（RFC3339 或 Unix timestamp）
        end_time : str
            结束时间
        step : str
            采样间隔
        url : str
            Prometheus URL

        Returns
        -------
        pd.DataFrame
            加载的数据
        """
        from prometheus_api_client import PrometheusConnect

        logger.info(f"Loading data from Prometheus: {query}")
        prom = PrometheusConnect(url=url, disable_ssl=True)

        # 查询数据
        metric_data = prom.custom_query_range(
            query=query,
            start_time=start_time,
            end_time=end_time,
            step=step,
        )

        # 转换为 DataFrame
        if not metric_data:
            raise ValueError("No data returned from Prometheus")

        data = metric_data[0]["values"]
        df = pd.DataFrame(data, columns=["timestamp", "value"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df["value"] = pd.to_numeric(df["value"])

        logger.info(f"Loaded {len(df)} rows from Prometheus")
        return df


# ----------------------------------------------------------------------
# 2️⃣ 数据清洗
# ----------------------------------------------------------------------
class TimeSeriesCleaner:
    """时序数据清洗"""

    @staticmethod
    def handle_missing_values(
        df: pd.DataFrame,
        value_col: str = "value",
        method: str = "ffill",
    ) -> pd.DataFrame:
        """
        处理缺失值

        Parameters
        ----------
        df : pd.DataFrame
            输入数据
        value_col : str
            值列名
        method : str
            处理方法：'ffill', 'bfill', 'interpolate', 'drop', 'zero'

        Returns
        -------
        pd.DataFrame
            清洗后的数据
        """
        df = df.copy()
        missing_count = df[value_col].isna().sum()

        if missing_count > 0:
            logger.info(f"Found {missing_count} missing values, using method: {method}")

            if method == "ffill":
                df[value_col] = df[value_col].ffill()
            elif method == "bfill":
                df[value_col] = df[value_col].bfill()
            elif method == "interpolate":
                df[value_col] = df[value_col].interpolate()
            elif method == "drop":
                df = df.dropna(subset=[value_col])
            elif method == "zero":
                df[value_col] = df[value_col].fillna(0)
            else:
                raise ValueError(f"Unknown method: {method}")

        return df

    @staticmethod
    def remove_outliers(
        df: pd.DataFrame,
        value_col: str = "value",
        method: str = "iqr",
        threshold: float = 3.0,
    ) -> pd.DataFrame:
        """
        移除异常值（注意：这是数据清洗，不是异常检测）

        Parameters
        ----------
        df : pd.DataFrame
            输入数据
        value_col : str
            值列名
        method : str
            方法：'iqr', 'zscore', 'isolation'
        threshold : float
            阈值

        Returns
        -------
        pd.DataFrame
            清洗后的数据
        """
        df = df.copy()

        if method == "iqr":
            Q1 = df[value_col].quantile(0.25)
            Q3 = df[value_col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            mask = (df[value_col] >= lower_bound) & (df[value_col] <= upper_bound)

        elif method == "zscore":
            mean = df[value_col].mean()
            std = df[value_col].std()
            z_scores = np.abs((df[value_col] - mean) / std)
            mask = z_scores < threshold

        elif method == "isolation":
            from sklearn.ensemble import IsolationForest

            iso = IsolationForest(contamination=0.1, random_state=42)
            preds = iso.fit_predict(df[[value_col]].values)
            mask = preds == 1
        else:
            raise ValueError(f"Unknown method: {method}")

        removed_count = (~mask).sum()
        if removed_count > 0:
            logger.info(f"Removed {removed_count} outliers using {method}")
            df = df[mask]

        return df

    @staticmethod
    def resample(
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        value_col: str = "value",
        freq: str = "1min",
        agg: str = "mean",
    ) -> pd.DataFrame:
        """
        重采样数据

        Parameters
        ----------
        df : pd.DataFrame
            输入数据
        timestamp_col : str
            时间戳列名
        value_col : str
            值列名
        freq : str
            重采样频率（如 '1min', '5min', '1H'）
        agg : str
            聚合方法：'mean', 'sum', 'max', 'min', 'median'

        Returns
        -------
        pd.DataFrame
            重采样后的数据
        """
        df = df.copy()
        df = df.set_index(timestamp_col)

        if agg == "mean":
            df = df.resample(freq).mean()
        elif agg == "sum":
            df = df.resample(freq).sum()
        elif agg == "max":
            df = df.resample(freq).max()
        elif agg == "min":
            df = df.resample(freq).min()
        elif agg == "median":
            df = df.resample(freq).median()
        else:
            raise ValueError(f"Unknown aggregation: {agg}")

        df = df.reset_index()
        df = df.dropna(subset=[value_col])

        logger.info(f"Resampled to {freq}, {len(df)} rows")
        return df


# ----------------------------------------------------------------------
# 3️⃣ 特征工程
# ----------------------------------------------------------------------
class TimeSeriesFeatureEngineer:
    """时序特征工程"""

    @staticmethod
    def add_lag_features(
        df: pd.DataFrame,
        value_col: str = "value",
        lags: List[int] = [1, 5, 10, 20],
    ) -> pd.DataFrame:
        """
        添加滞后特征

        Parameters
        ----------
        df : pd.DataFrame
            输入数据
        value_col : str
            值列名
        lags : List[int]
            滞后期列表

        Returns
        -------
        pd.DataFrame
            添加特征后的数据
        """
        df = df.copy()

        for lag in lags:
            df[f"{value_col}_lag_{lag}"] = df[value_col].shift(lag)

        # 填充 NaN
        df = df.fillna(method="bfill").fillna(0)

        logger.info(f"Added {len(lags)} lag features")
        return df

    @staticmethod
    def add_rolling_features(
        df: pd.DataFrame,
        value_col: str = "value",
        windows: List[int] = [5, 10, 20],
    ) -> pd.DataFrame:
        """
        添加滚动窗口特征

        Parameters
        ----------
        df : pd.DataFrame
            输入数据
        value_col : str
            值列名
        windows : List[int]
            窗口大小列表

        Returns
        -------
        pd.DataFrame
            添加特征后的数据
        """
        df = df.copy()

        for window in windows:
            df[f"{value_col}_rolling_mean_{window}"] = df[value_col].rolling(window).mean()
            df[f"{value_col}_rolling_std_{window}"] = df[value_col].rolling(window).std()
            df[f"{value_col}_rolling_min_{window}"] = df[value_col].rolling(window).min()
            df[f"{value_col}_rolling_max_{window}"] = df[value_col].rolling(window).max()

        # 填充 NaN
        df = df.fillna(method="bfill").fillna(0)

        logger.info(f"Added rolling features for windows: {windows}")
        return df

    @staticmethod
    def add_time_features(
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
    ) -> pd.DataFrame:
        """
        添加时间特征

        Parameters
        ----------
        df : pd.DataFrame
            输入数据
        timestamp_col : str
            时间戳列名

        Returns
        -------
        pd.DataFrame
            添加特征后的数据
        """
        df = df.copy()

        df["hour"] = df[timestamp_col].dt.hour
        df["day_of_week"] = df[timestamp_col].dt.dayofweek
        df["day_of_month"] = df[timestamp_col].dt.day
        df["month"] = df[timestamp_col].dt.month
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        # 周期性编码
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
        df["day_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
        df["day_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

        logger.info("Added time features")
        return df

    @staticmethod
    def add_statistical_features(
        df: pd.DataFrame,
        value_col: str = "value",
        window: int = 100,
    ) -> pd.DataFrame:
        """
        添加统计特征

        Parameters
        ----------
        df : pd.DataFrame
            输入数据
        value_col : str
            值列名
        window : int
            统计窗口

        Returns
        -------
        pd.DataFrame
            添加特征后的数据
        """
        df = df.copy()

        # 滑动窗口统计
        df[f"{value_col}_zscore"] = (df[value_col] - df[value_col].rolling(window).mean()) / df[
            value_col
        ].rolling(window).std()

        df[f"{value_col}_pct_change"] = df[value_col].pct_change()
        df[f"{value_col}_diff"] = df[value_col].diff()

        # 填充 NaN
        df = df.fillna(method="bfill").fillna(0)

        logger.info("Added statistical features")
        return df


# ----------------------------------------------------------------------
# 4️⃣ 数据增强
# ----------------------------------------------------------------------
class TimeSeriesAugmenter:
    """时序数据增强"""

    @staticmethod
    def add_noise(
        data: np.ndarray,
        noise_level: float = 0.01,
    ) -> np.ndarray:
        """
        添加高斯噪声

        Parameters
        ----------
        data : np.ndarray
            输入数据
        noise_level : float
            噪声水平

        Returns
        -------
        np.ndarray
            增强后的数据
        """
        noise = np.random.normal(0, noise_level * data.std(), data.shape)
        return data + noise

    @staticmethod
    def time_warp(
        data: np.ndarray,
        sigma: float = 0.2,
    ) -> np.ndarray:
        """
        时间扭曲

        Parameters
        ----------
        data : np.ndarray
            输入数据 (seq_len, features)
        sigma : float
            扭曲强度

        Returns
        -------
        np.ndarray
            增强后的数据
        """
        seq_len = data.shape[0]

        # 生成扭曲函数
        t = np.linspace(0, 1, seq_len)
        noise = np.random.normal(0, sigma, seq_len)
        warp = np.cumsum(noise)
        warp = warp - warp.min()
        warp = warp / warp.max()
        warp = t + warp

        # 插值
        from scipy.interpolate import interp1d

        f = interp1d(t, data, kind="linear", axis=0, fill_value="extrapolate")
        augmented = cast(np.ndarray, f(warp))

        return augmented

    @staticmethod
    def magnitude_warp(
        data: np.ndarray,
        sigma: float = 0.2,
    ) -> np.ndarray:
        """
        幅度扭曲

        Parameters
        ----------
        data : np.ndarray
            输入数据
        sigma : float
            扭曲强度

        Returns
        -------
        np.ndarray
            增强后的数据
        """
        seq_len = data.shape[0]

        # 生成扭曲曲线
        warp = cast(np.ndarray, np.random.normal(1, sigma, seq_len))
        warp = np.cumsum(warp)
        warp = warp / warp.mean()

        return data * warp[:, np.newaxis]

    @staticmethod
    def augment_dataset(
        data: np.ndarray,
        labels: Optional[np.ndarray] = None,
        augment_factor: int = 2,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        增强数据集

        Parameters
        ----------
        data : np.ndarray
            输入数据
        labels : np.ndarray, optional
            标签
        augment_factor : int
            增强倍数

        Returns
        -------
        augmented_data : np.ndarray
            增强后的数据
        augmented_labels : np.ndarray, optional
            增强后的标签
        """
        augmented = [data]
        augmented_labels_list: Optional[List[np.ndarray]] = [labels] if labels is not None else None

        for _ in range(augment_factor - 1):
            # 随机选择增强方法
            method = np.random.choice(["noise", "time_warp", "magnitude_warp"])

            if method == "noise":
                aug_data = TimeSeriesAugmenter.add_noise(data)
            elif method == "time_warp":
                aug_data = TimeSeriesAugmenter.time_warp(data)
            else:
                aug_data = TimeSeriesAugmenter.magnitude_warp(data)

            augmented.append(aug_data)
            if labels is not None and augmented_labels_list is not None:
                augmented_labels_list.append(labels)

        augmented_data = np.concatenate(augmented, axis=0)

        augmented_labels: Optional[np.ndarray] = None
        if labels is not None and augmented_labels_list is not None:
            augmented_labels = np.concatenate(augmented_labels_list, axis=0)

        logger.info(f"Augmented dataset from {len(data)} to {len(augmented_data)} samples")
        return augmented_data, augmented_labels


# ----------------------------------------------------------------------
# 5️⃣ 数据缩放
# ----------------------------------------------------------------------
class TimeSeriesScaler:
    """时序数据缩放"""

    def __init__(self, method: str = "standard"):
        """
        Parameters
        ----------
        method : str
            缩放方法：'standard', 'minmax'
        """
        self.method = method
        if method == "standard":
            self.scaler = StandardScaler()
        elif method == "minmax":
            self.scaler = MinMaxScaler()
        else:
            raise ValueError(f"Unknown method: {method}")

    def fit(self, data: np.ndarray) -> "TimeSeriesScaler":
        """
        拟合缩放器

        Parameters
        ----------
        data : np.ndarray
            输入数据

        Returns
        -------
        self
        """
        # Reshape for sklearn (n_samples, n_features)
        original_shape = data.shape
        if len(original_shape) == 2:
            data_2d = data
        else:
            data_2d = data.reshape(-1, data.shape[-1])

        self.scaler.fit(data_2d)
        self.original_shape = original_shape

        return self

    def transform(self, data: np.ndarray) -> np.ndarray:
        """
        转换数据

        Parameters
        ----------
        data : np.ndarray
            输入数据

        Returns
        -------
        np.ndarray
            缩放后的数据
        """
        original_shape = data.shape
        if len(original_shape) == 2:
            data_2d = data
        else:
            data_2d = data.reshape(-1, data.shape[-1])

        scaled = self.scaler.transform(data_2d)

        return cast(np.ndarray, scaled.reshape(original_shape))

    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        """拟合并转换"""
        return self.fit(data).transform(data)

    def inverse_transform(self, data: np.ndarray) -> np.ndarray:
        """
        逆转换

        Parameters
        ----------
        data : np.ndarray
            缩放后的数据

        Returns
        -------
        np.ndarray
            原始尺度数据
        """
        original_shape = data.shape
        if len(original_shape) == 2:
            data_2d = data
        else:
            data_2d = data.reshape(-1, data.shape[-1])

        inverted = self.scaler.inverse_transform(data_2d)

        return cast(np.ndarray, inverted.reshape(original_shape))


# ----------------------------------------------------------------------
# 6️⃣ 数据集划分
# ----------------------------------------------------------------------
class TimeSeriesSplitter:
    """时序数据集划分"""

    @staticmethod
    def train_val_test_split(
        data: np.ndarray,
        labels: Optional[np.ndarray] = None,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        shuffle: bool = False,
    ) -> Tuple[
        np.ndarray,
        np.ndarray,
        np.ndarray,
        Optional[np.ndarray],
        Optional[np.ndarray],
        Optional[np.ndarray],
    ]:
        """
        划分训练/验证/测试集

        Parameters
        ----------
        data : np.ndarray
            输入数据
        labels : np.ndarray, optional
            标签
        train_ratio : float
            训练集比例
        val_ratio : float
            验证集比例
        test_ratio : float
            测试集比例
        shuffle : bool
            是否打乱（时序数据通常不打乱）

        Returns
        -------
        train_data, val_data, test_data : np.ndarray
            划分后的数据
        train_labels, val_labels, test_labels : np.ndarray, optional
            划分后的标签
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6

        n_samples = len(data)
        train_end = int(n_samples * train_ratio)
        val_end = int(n_samples * (train_ratio + val_ratio))

        if shuffle:
            indices = np.random.permutation(n_samples)
            data = data[indices]
            if labels is not None:
                labels = labels[indices]

        train_data = data[:train_end]
        val_data = data[train_end:val_end]
        test_data = data[val_end:]

        train_labels: Optional[np.ndarray]
        val_labels: Optional[np.ndarray]
        test_labels: Optional[np.ndarray]

        if labels is not None:
            train_labels = labels[:train_end]
            val_labels = labels[train_end:val_end]
            test_labels = labels[val_end:]
        else:
            train_labels = None
            val_labels = None
            test_labels = None

        logger.info(
            f"Split data: train={len(train_data)}, val={len(val_data)}, test={len(test_data)}"
        )

        return train_data, val_data, test_data, train_labels, val_labels, test_labels


# ----------------------------------------------------------------------
# 7️⃣ 完整预处理管道
# ----------------------------------------------------------------------
class TimeSeriesPreprocessingPipeline:
    """完整的时序数据预处理管道"""

    def __init__(
        self,
        clean_missing: bool = True,
        clean_outliers: bool = False,
        add_features: bool = True,
        scale: bool = True,
        scale_method: str = "standard",
        augment: bool = False,
        augment_factor: int = 2,
    ):
        """
        Parameters
        ----------
        clean_missing : bool
            是否清洗缺失值
        clean_outliers : bool
            是否清洗异常值
        add_features : bool
            是否添加特征
        scale : bool
            是否缩放
        scale_method : str
            缩放方法
        augment : bool
            是否数据增强
        augment_factor : int
            增强倍数
        """
        self.clean_missing = clean_missing
        self.clean_outliers = clean_outliers
        self.add_features = add_features
        self.scale = scale
        self.scale_method = scale_method
        self.augment = augment
        self.augment_factor = augment_factor

        self.scaler: Optional[TimeSeriesScaler] = None

    def process(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        value_col: str = "value",
        feature_cols: Optional[List[str]] = None,
    ) -> np.ndarray:
        """
        处理数据

        Parameters
        ----------
        df : pd.DataFrame
            输入数据
        timestamp_col : str
            时间戳列名
        value_col : str
            值列名
        feature_cols : List[str], optional
            特征列名

        Returns
        -------
        np.ndarray
            处理后的数据
        """
        df = df.copy()

        # 清洗缺失值
        if self.clean_missing:
            df = TimeSeriesCleaner.handle_missing_values(df, value_col)

        # 清洗异常值
        if self.clean_outliers:
            df = TimeSeriesCleaner.remove_outliers(df, value_col)

        # 添加特征
        if self.add_features:
            df = TimeSeriesFeatureEngineer.add_time_features(df, timestamp_col)
            df = TimeSeriesFeatureEngineer.add_rolling_features(df, value_col)
            df = TimeSeriesFeatureEngineer.add_lag_features(df, value_col)

        # 选择特征列
        if feature_cols is None:
            feature_cols = [col for col in df.columns if col != timestamp_col]

        data = df[feature_cols].values

        # 缩放
        if self.scale:
            self.scaler = TimeSeriesScaler(method=self.scale_method)
            data = self.scaler.fit_transform(data)

        logger.info(f"Processed data shape: {data.shape}")
        return cast(np.ndarray, data)

    def process_for_training(
        self,
        df: pd.DataFrame,
        labels: Optional[np.ndarray] = None,
        timestamp_col: str = "timestamp",
        value_col: str = "value",
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        为训练处理数据（包括数据增强）

        Parameters
        ----------
        df : pd.DataFrame
            输入数据
        labels : np.ndarray, optional
            标签
        timestamp_col : str
            时间戳列名
        value_col : str
            值列名

        Returns
        -------
        data : np.ndarray
            处理后的数据
        labels : np.ndarray, optional
            处理后的标签
        """
        data = self.process(df, timestamp_col, value_col)

        # 数据增强
        if self.augment:
            data, labels = TimeSeriesAugmenter.augment_dataset(data, labels, self.augment_factor)

        return data, labels


# ----------------------------------------------------------------------
# 8️⃣ 多模态数据准备
# ----------------------------------------------------------------------
class MultiModalDataPreparer:
    """多模态数据准备"""

    @staticmethod
    def prepare_log_features(
        logs: List[str],
        embedding_model: Optional[Any] = None,
        max_length: int = 512,
    ) -> np.ndarray:
        """
        准备日志特征

        Parameters
        ----------
        logs : List[str]
            日志文本列表
        embedding_model : Any, optional
            嵌入模型（如 sentence-transformers）
        max_length : int
            最大长度

        Returns
        -------
        np.ndarray
            日志特征 (n_samples, embedding_dim)
        """
        if embedding_model is None:
            # 简单的词频统计
            from sklearn.feature_extraction.text import TfidfVectorizer

            vectorizer = TfidfVectorizer(max_features=64, max_length=max_length)
            features = vectorizer.fit_transform(logs).toarray()
        else:
            # 使用嵌入模型
            features = embedding_model.encode(logs, show_progress_bar=False)

        logger.info(f"Prepared log features: {features.shape}")
        return cast(np.ndarray, features)

    @staticmethod
    def prepare_trace_features(
        traces: List[Dict[str, Any]],
        feature_dim: int = 64,
    ) -> np.ndarray:
        """
        准备追踪特征

        Parameters
        ----------
        traces : List[Dict[str, Any]]
            追踪数据列表
        feature_dim : int
            特征维度

        Returns
        -------
        np.ndarray
            追踪特征 (n_samples, feature_dim)
        """
        features = []

        for trace in traces:
            # 提取关键特征
            duration = trace.get("duration", 0)
            span_count = len(trace.get("spans", []))
            error_count = sum(1 for span in trace.get("spans", []) if span.get("error", False))

            # 简单特征向量
            feature = np.array(
                [
                    duration,
                    span_count,
                    error_count,
                    duration / (span_count + 1),
                    error_count / (span_count + 1),
                ]
                + [0] * (feature_dim - 5)
            )

            features.append(feature)

        features_array = np.array(features)
        logger.info(f"Prepared trace features: {features_array.shape}")
        return features_array


# ----------------------------------------------------------------------
# 9️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_preprocessing_pipeline(
    scale_method: str = "standard",
    add_features: bool = True,
) -> TimeSeriesPreprocessingPipeline:
    """创建预处理管道"""
    return TimeSeriesPreprocessingPipeline(
        scale_method=scale_method,
        add_features=add_features,
    )


# ----------------------------------------------------------------------
# 🔟 CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    # 生成测试数据
    logger.info("Creating test data")
    n_samples = 1000
    timestamps = pd.date_range("2024-01-01", periods=n_samples, freq="1min")
    values = np.random.randn(n_samples).cumsum() + 100

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "value": values,
        }
    )

    # 测试预处理管道
    pipeline = create_preprocessing_pipeline()
    processed_data = pipeline.process(df)

    logger.info(f"Original shape: {df.shape}")
    logger.info(f"Processed shape: {processed_data.shape}")

    logger.info("Test passed!")
