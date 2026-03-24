from __future__ import annotations

from copy import deepcopy

import pandas as pd


class BaseStrategy:
    slug = ""
    name = ""
    category = ""
    description = ""
    default_params: dict = {}
    signal_family = "generic"

    def normalize_params(self, params: dict | None) -> dict:
        merged = deepcopy(self.default_params)
        for key, value in (params or {}).items():
            if value is not None:
                merged[key] = value
        return merged

    def compute_features(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        return df

    def generate_signal(self, df: pd.DataFrame, params: dict) -> pd.Series:
        raise NotImplementedError

    def signal_strength(self, df: pd.DataFrame, params: dict) -> pd.Series:
        raise NotImplementedError

    def backtest(self, df: pd.DataFrame, params: dict) -> dict:
        raise NotImplementedError

    def describe_signal_math(
        self,
        df: pd.DataFrame,
        params: dict,
        signal_series: pd.Series,
        strength_series: pd.Series,
    ) -> dict:
        return {
            "signal_formula": "Strategy-specific signal rule.",
            "strength_formula": "Strategy-specific strength normalization.",
            "signal_active": self.latest_boolean(signal_series),
            "strength": self.latest_float(strength_series),
            "inputs": {},
        }

    @staticmethod
    def latest_boolean(series: pd.Series) -> bool:
        cleaned = series.dropna()
        return bool(cleaned.iloc[-1]) if not cleaned.empty else False

    @staticmethod
    def latest_float(series: pd.Series, default: float = 0.0) -> float:
        cleaned = pd.to_numeric(series, errors="coerce").dropna()
        return float(cleaned.iloc[-1]) if not cleaned.empty else float(default)
