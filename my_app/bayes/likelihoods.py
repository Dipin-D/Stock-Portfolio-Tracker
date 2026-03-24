from __future__ import annotations

import math

import pandas as pd


EPSILON = 1e-9


def estimate_binary_likelihood(
    signal_series: pd.Series,
    target_series: pd.Series,
    observed_event: bool,
    alpha: float = 1.0,
) -> dict:
    prepared = pd.DataFrame({
        "signal": signal_series,
        "target": target_series,
    }).dropna()

    if prepared.empty:
        return {
            "alpha": float(alpha),
            "observed_event": bool(observed_event),
            "probability_given_success": 0.5,
            "probability_given_failure": 0.5,
            "likelihood_ratio": 1.0,
            "log_likelihood_ratio": 0.0,
            "support": {
                "success_total": 0,
                "failure_total": 0,
                "success_event": 0,
                "failure_event": 0,
            },
        }

    prepared["signal"] = prepared["signal"].astype(bool)
    prepared["target"] = prepared["target"].astype(int)

    event_series = prepared["signal"] if observed_event else ~prepared["signal"]
    success_total = int((prepared["target"] == 1).sum())
    failure_total = int((prepared["target"] == 0).sum())
    success_event = int((event_series & prepared["target"].eq(1)).sum())
    failure_event = int((event_series & prepared["target"].eq(0)).sum())

    probability_given_success = (success_event + alpha) / (success_total + 2 * alpha) if success_total or alpha else 0.5
    probability_given_failure = (failure_event + alpha) / (failure_total + 2 * alpha) if failure_total or alpha else 0.5
    likelihood_ratio = probability_given_success / max(probability_given_failure, EPSILON)

    return {
        "alpha": float(alpha),
        "observed_event": bool(observed_event),
        "probability_given_success": float(probability_given_success),
        "probability_given_failure": float(probability_given_failure),
        "likelihood_ratio": float(likelihood_ratio),
        "log_likelihood_ratio": float(math.log(max(likelihood_ratio, EPSILON))),
        "support": {
            "success_total": success_total,
            "failure_total": failure_total,
            "success_event": success_event,
            "failure_event": failure_event,
        },
    }
