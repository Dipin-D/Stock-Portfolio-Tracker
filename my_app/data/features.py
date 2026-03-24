from __future__ import annotations

import numpy as np
import pandas as pd


def _normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    if pd.api.types.is_numeric_dtype(normalized["Date"]):
        normalized["Date_dt"] = pd.to_datetime(normalized["Date"], unit="s", errors="coerce")
    else:
        normalized["Date_dt"] = pd.to_datetime(normalized["Date"], errors="coerce")
    normalized = normalized.dropna(subset=["Date_dt"]).sort_values("Date_dt").reset_index(drop=True)
    normalized["Date"] = normalized["Date_dt"].apply(lambda value: value.timestamp())
    return normalized


def build_feature_matrix(
    price_frame: pd.DataFrame,
    benchmark_frame: pd.DataFrame | None = None,
    horizon_days: int = 126,
) -> pd.DataFrame:
    df = _normalize_dates(price_frame)
    close = df["Close"].astype(float)
    returns = close.pct_change()

    df["ret_1"] = close.pct_change(1)
    df["ret_5"] = close.pct_change(5)
    df["ret_21"] = close.pct_change(21)
    df["ret_63"] = close.pct_change(63)
    df["ret_126"] = close.pct_change(126)
    df["ret_252"] = close.pct_change(252)

    df["vol_21"] = returns.rolling(21).std()
    df["vol_63"] = returns.rolling(63).std()
    df["vol_126"] = returns.rolling(126).std()

    df["sma_20"] = close.rolling(20).mean()
    if "sma_50" not in df.columns:
        df["sma_50"] = close.rolling(50).mean()
    if "sma_200" not in df.columns:
        df["sma_200"] = close.rolling(200).mean()
    df["ema_20"] = close.ewm(span=20, adjust=False).mean()
    df["ema_50"] = close.ewm(span=50, adjust=False).mean()

    df["price_to_sma50"] = close / df["sma_50"]
    df["price_to_sma200"] = close / df["sma_200"]
    df["dist_52w_high"] = close / close.rolling(252).max() - 1.0
    df["rolling_max_drawdown_126"] = close / close.rolling(126).max() - 1.0
    df["sharpe_proxy_63"] = df["ret_63"] / df["vol_63"].replace(0, np.nan)

    if benchmark_frame is not None and not benchmark_frame.empty:
        benchmark = _normalize_dates(benchmark_frame)[["Date_dt", "Close"]].rename(columns={"Close": "benchmark_close"})
        benchmark["benchmark_ret_126"] = benchmark["benchmark_close"].pct_change(126)
        benchmark["benchmark_future_ret_126"] = benchmark["benchmark_close"].shift(-horizon_days) / benchmark["benchmark_close"] - 1
        df = df.merge(benchmark, on="Date_dt", how="left")
        df["benchmark_relative_ret_126"] = df["ret_126"] - df["benchmark_ret_126"]
    else:
        df["benchmark_close"] = np.nan
        df["benchmark_ret_126"] = np.nan
        df["benchmark_future_ret_126"] = np.nan
        df["benchmark_relative_ret_126"] = np.nan

    df["future_ret_126"] = close.shift(-horizon_days) / close - 1.0
    df["future_relative_ret_126"] = df["future_ret_126"] - df["benchmark_future_ret_126"]
    df["target_success"] = np.where(df["future_ret_126"].notna(), (df["future_ret_126"] > 0).astype(int), np.nan)
    return df

