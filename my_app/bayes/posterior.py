from __future__ import annotations

import math

import pandas as pd


EPSILON = 1e-9


def clamp_probability(probability: float) -> float:
    return min(max(float(probability), EPSILON), 1.0 - EPSILON)


def probability_to_log_odds(probability: float) -> float:
    probability = clamp_probability(probability)
    return math.log(probability / (1.0 - probability))


def log_odds_to_probability(log_odds: float) -> float:
    odds = math.exp(log_odds)
    return float(odds / (1.0 + odds))


def apply_evidence(prior_probability: float, likelihood_ratio: float, weight: float = 1.0) -> tuple[float, float]:
    prior_log_odds = probability_to_log_odds(prior_probability)
    weighted_log_lr = math.log(max(float(likelihood_ratio), EPSILON)) * float(weight)
    posterior = log_odds_to_probability(prior_log_odds + weighted_log_lr)
    return posterior, weighted_log_lr


def estimate_signal_weight(signal_series: pd.Series, previous_signal_series: list[pd.Series]) -> float:
    if not previous_signal_series:
        return 1.0

    candidate = signal_series.astype(float)
    correlations: list[float] = []
    for previous in previous_signal_series:
        aligned = pd.concat([candidate, previous.astype(float)], axis=1).dropna()
        if len(aligned) < 30:
            continue
        correlation = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
        if pd.notna(correlation):
            correlations.append(abs(float(correlation)))

    if not correlations:
        return 1.0

    average_correlation = sum(correlations) / len(correlations)
    return max(0.35, min(1.0, 1.0 - (average_correlation * 0.5)))


def confidence_label(probability: float) -> str:
    probability = float(probability)
    if probability >= 0.75:
        return "High"
    if probability >= 0.6:
        return "Moderate"
    if probability >= 0.45:
        return "Balanced"
    return "Low"

