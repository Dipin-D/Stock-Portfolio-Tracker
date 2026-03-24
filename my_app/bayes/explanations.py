from __future__ import annotations


def build_backtest_explanation(
    prior_probability: float,
    posterior_probability: float,
    evidence_items: list[dict],
    prior_mode: str,
    analysis_mode: str,
) -> dict:
    ordered = sorted(evidence_items, key=lambda item: item.get("weighted_log_lr", 0.0), reverse=True)
    positive = [item for item in ordered if item.get("weighted_log_lr", 0.0) > 0]
    negative = [item for item in ordered if item.get("weighted_log_lr", 0.0) < 0]

    notes = [
        f"Prior source: {'Golden Cross' if prior_mode == 'golden_cross' else 'Universe'}",
        f"Analysis mode: {'Multi-Strategy Analysis' if analysis_mode == 'multi' else 'Single Strategy Analysis'}",
    ]

    if len(evidence_items) > 1:
        notes.append("Correlation penalty applied across overlapping strategy signals.")
    elif evidence_items:
        notes.append("Posterior currently reflects one strategy evidence stream.")

    lift = posterior_probability - prior_probability
    notes.append(
        f"Posterior lift versus prior: {lift:+.2%}."
    )

    return {
        "top_positive_driver": positive[0]["slug"] if positive else "none",
        "top_negative_driver": negative[0]["slug"] if negative else "none",
        "notes": notes,
        "contributions": [
            {
                "slug": item["slug"],
                "name": item["name"],
                "weighted_log_lr": float(item.get("weighted_log_lr", 0.0)),
                "posterior_after": float(item.get("posterior_after", prior_probability)),
                "signal_active": bool(item.get("signal_active", False)),
                "used_as_prior": bool(item.get("used_as_prior", False)),
            }
            for item in evidence_items
        ],
    }

