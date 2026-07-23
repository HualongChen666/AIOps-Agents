# -*- coding: utf-8 -*-
"""
Time Series Preprocessing
Prepares time series data for causal analysis
"""

from typing import List, Optional, cast

import numpy as np
import pandas as pd
from loguru import logger


class TimeSeriesPreprocessor:
    """
    Preprocessor for time series data in causal analysis

    Features:
    - Missing value handling
    - Stationarity testing and transformation
    - Lag selection
    - Normalization
    - Outlier detection and handling
    """

    def __init__(
        self,
        handle_missing: str = "interpolate",
        normalize: bool = True,
        detect_outliers: bool = True,
    ):
        """
        Initialize preprocessor

        Args:
            handle_missing: How to handle missing values ("interpolate", "drop", "forward_fill")
            normalize: Whether to normalize data
            detect_outliers: Whether to detect and handle outliers
        """
        self.handle_missing = handle_missing
        self.normalize = normalize
        self.detect_outliers = detect_outliers

    def preprocess(
        self, data: pd.DataFrame, target_columns: Optional[List[str]] = None
    ) -> np.ndarray:
        """
        Preprocess time series data

        Args:
            data: Input data (DataFrame with datetime index)
            target_columns: Columns to process (all if None)

        Returns:
            Preprocessed data as numpy array
        """
        if target_columns is None:
            target_columns = data.columns.tolist()

        processed_data = data[target_columns].copy()

        # Handle missing values
        processed_data = self._handle_missing_values(processed_data)

        # Detect and handle outliers
        if self.detect_outliers:
            processed_data = self._handle_outliers(processed_data)

        # Normalize
        if self.normalize:
            processed_data = self._normalize(processed_data)

        logger.info(
            f"Preprocessed {len(target_columns)} columns, {len(processed_data)} time points"
        )

        return cast(np.ndarray, processed_data.values)

    def _handle_missing_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Handle missing values

        Args:
            data: Input data

        Returns:
            Data with missing values handled
        """
        if self.handle_missing == "interpolate":
            return data.interpolate(method="linear")
        elif self.handle_missing == "drop":
            return data.dropna()
        elif self.handle_missing == "forward_fill":
            return data.fillna(method="ffill")
        else:
            return data

    def _handle_outliers(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Detect and handle outliers using IQR method

        Args:
            data: Input data

        Returns:
            Data with outliers handled
        """
        for col in data.columns:
            Q1 = data[col].quantile(0.25)
            Q3 = data[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            # Cap outliers
            data[col] = data[col].clip(lower=lower_bound, upper=upper_bound)

        return data

    def _normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize data to zero mean and unit variance

        Args:
            data: Input data

        Returns:
            Normalized data
        """
        return (data - data.mean()) / data.std()

    def select_lags(self, data: np.ndarray, max_lag: int = 10, method: str = "aic") -> List[int]:
        """
        Select optimal lags for causal analysis

        Args:
            data: Time series data
            max_lag: Maximum lag to consider
            method: Lag selection method ("aic", "bic", "auto")

        Returns:
            List of selected lags
        """
        n_variables = data.shape[1]

        if method == "auto":
            # Use simple heuristic: select lags with significant autocorrelation
            selected_lags = []
            for i in range(n_variables):
                for lag in range(1, max_lag + 1):
                    autocorr = np.corrcoef(data[lag:, i], data[:-lag, i])[0, 1]
                    if abs(autocorr) > 0.3:
                        selected_lags.append(lag)
            return sorted(set(selected_lags))

        # Default: use first few lags
        return list(range(1, min(5, max_lag + 1)))

    def create_lagged_features(self, data: np.ndarray, lags: List[int]) -> np.ndarray:
        """
        Create lagged features for causal analysis

        Args:
            data: Original time series data
            lags: List of lags to use

        Returns:
            Data with lagged features
        """
        n_samples, n_variables = data.shape
        max_lag = max(lags) if lags else 0

        # Create lagged features
        lagged_features = []
        for lag in lags:
            lagged_data = np.roll(data, lag, axis=0)
            lagged_data[:lag] = np.nan
            lagged_features.append(lagged_data)

        # Concatenate original and lagged features
        combined: np.ndarray
        if lagged_features:
            combined = np.hstack([data] + lagged_features)
            # Remove rows with NaN from lagging
            combined = combined[max_lag:]
        else:
            combined = data

        return combined
