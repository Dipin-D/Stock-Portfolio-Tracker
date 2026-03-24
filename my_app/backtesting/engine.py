from __future__ import annotations


def run_strategy_backtest(strategy, feature_frame, params: dict) -> dict:
    return strategy.backtest(feature_frame, params)

