from __future__ import annotations

from typing import Iterable

import pandas as pd

from my_app.utils import PriceDataError, download_n_clean_data

from .features import build_feature_matrix


def load_price_frame(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    return download_n_clean_data(symbol.replace(".", "-"), start_date, end_date, compute_sma=True)


def load_feature_frame(
    symbol: str,
    start_date: str,
    end_date: str,
    benchmark: str = "SPY",
    horizon_days: int = 126,
) -> pd.DataFrame:
    price_frame = load_price_frame(symbol, start_date, end_date)
    benchmark_frame = None
    if benchmark and benchmark.upper() != symbol.upper():
        benchmark_frame = load_price_frame(benchmark, start_date, end_date)
    return build_feature_matrix(price_frame, benchmark_frame=benchmark_frame, horizon_days=horizon_days)


def load_training_frames(
    symbols: Iterable[str],
    start_date: str,
    end_date: str,
    benchmark: str = "SPY",
    horizon_days: int = 126,
) -> tuple[list[pd.DataFrame], list[str], dict[str, str]]:
    benchmark_frame = None
    benchmark_symbol = (benchmark or "").upper().strip()
    if benchmark_symbol:
        try:
            benchmark_frame = load_price_frame(benchmark_symbol, start_date, end_date)
        except PriceDataError:
            benchmark_frame = None

    frames: list[pd.DataFrame] = []
    loaded_symbols: list[str] = []
    errors: dict[str, str] = {}

    for symbol in symbols:
        normalized = (symbol or "").upper().strip()
        if not normalized:
            continue

        try:
            price_frame = load_price_frame(normalized, start_date, end_date)
            reference_benchmark = None if benchmark_frame is None or normalized == benchmark_symbol else benchmark_frame
            frames.append(build_feature_matrix(price_frame, benchmark_frame=reference_benchmark, horizon_days=horizon_days))
            loaded_symbols.append(normalized)
        except PriceDataError as error:
            errors[normalized] = str(error)

    if not frames:
        raise PriceDataError("Unable to load enough historical data to estimate priors and likelihoods.")

    return frames, loaded_symbols, errors

