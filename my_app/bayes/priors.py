from __future__ import annotations

import pandas as pd


def estimate_universe_prior(training_frames: list[pd.DataFrame], alpha: float = 1.0) -> dict:
    target = pd.concat([frame["target_success"] for frame in training_frames], ignore_index=True).dropna()
    successes = int((target == 1).sum())
    total = int(len(target))
    prior = (successes + alpha) / (total + 2 * alpha) if total or alpha else 0.5
    return {
        "mode": "universe",
        "alpha": float(alpha),
        "probability": float(prior),
        "support": {
            "successes": successes,
            "total": total,
        },
    }


def estimate_conditional_prior(
    strategy,
    training_frames: list[pd.DataFrame],
    params: dict,
    observed_event: bool,
    alpha: float = 1.0,
) -> dict:
    successes = 0
    total = 0

    for frame in training_frames:
        strategy_frame = strategy.compute_features(frame.copy(), params)
        signal = strategy.generate_signal(strategy_frame, params)
        prepared = pd.DataFrame({
            "signal": signal,
            "target": strategy_frame["target_success"],
        }).dropna()
        if prepared.empty:
            continue

        prepared["signal"] = prepared["signal"].astype(bool)
        prepared["target"] = prepared["target"].astype(int)
        event_mask = prepared["signal"] if observed_event else ~prepared["signal"]
        subset = prepared.loc[event_mask]
        if subset.empty:
            continue

        successes += int((subset["target"] == 1).sum())
        total += int(len(subset))

    probability = (successes + alpha) / (total + 2 * alpha) if total or alpha else 0.5
    return {
        "mode": "golden_cross",
        "alpha": float(alpha),
        "probability": float(probability),
        "support": {
            "successes": successes,
            "total": total,
            "observed_event": bool(observed_event),
        },
    }
