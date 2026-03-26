from __future__ import annotations

from datetime import date, datetime

from django.db import transaction

from my_app.backtesting.earnings import (
    MODE_CUSTOM,
    MODE_NEVER_TRADE,
    MODE_NOTHING_SPECIAL,
    MODE_ONLY_TRADE,
    normalize_earnings_config,
    resolve_earnings_config,
)
from my_app.bayes.explanations import build_backtest_explanation
from my_app.bayes.likelihoods import estimate_binary_likelihood
from my_app.bayes.posterior import (
    apply_evidence,
    confidence_label,
    estimate_signal_weight,
    probability_to_log_odds,
)
from my_app.bayes.priors import estimate_conditional_prior, estimate_universe_prior
from my_app.data.loaders import load_feature_frame, load_training_frames
from my_app.data.universe import build_training_universe
from my_app.models import BacktestRun, EvidenceSnapshot, StrategyDefinition, StrategyRun, TradeLog
from my_app.strategies import get_strategy, get_supported_strategies


SUPPORTED_PRIOR_MODES = {
    BacktestRun.PRIOR_MODE_UNIVERSE,
    BacktestRun.PRIOR_MODE_GOLDEN_CROSS,
}

SUPPORTED_ANALYSIS_MODES = {
    BacktestRun.ANALYSIS_MODE_SINGLE,
    BacktestRun.ANALYSIS_MODE_MULTI,
}

BAYES_GLOSSARY = [
    {
        "term": "Prior Probability",
        "definition": "The starting belief about trade success before the current evidence step is applied.",
    },
    {
        "term": "Likelihood Ratio",
        "definition": "How much more likely the observed strategy event is in successful outcomes versus failed outcomes.",
    },
    {
        "term": "Weighted Log-LR",
        "definition": "The log of the likelihood ratio after the correlation penalty weight is applied.",
    },
    {
        "term": "Posterior Probability",
        "definition": "The updated belief after folding the current strategy evidence into the prior.",
    },
]


def _earnings_mode_label(mode: str, custom_mode: str = MODE_NEVER_TRADE) -> str:
    normalized_mode = (mode or MODE_NOTHING_SPECIAL).strip().lower()
    if normalized_mode == MODE_NEVER_TRADE:
        return "Never Trade Earnings"
    if normalized_mode == MODE_ONLY_TRADE:
        return "Only Trade Earnings"
    if normalized_mode == MODE_CUSTOM:
        if (custom_mode or "").strip().lower() == MODE_ONLY_TRADE:
            return "Custom Earnings (Only Trade)"
        return "Custom Earnings (Never Trade)"
    return "Nothing Special"


def _enrich_earnings_payload(raw_payload: dict, blocked_entries_total: int) -> dict:
    payload = dict(raw_payload or {})
    dates_count = len(payload.get("earnings_dates") or [])
    before_days = int(payload.get("blackout_before_days") or 0)
    after_days = int(payload.get("blackout_after_days") or 0)
    mode = (payload.get("mode") or MODE_NOTHING_SPECIAL).strip().lower()
    custom_mode = (payload.get("custom_mode") or MODE_NEVER_TRADE).strip().lower()
    mode_label = _earnings_mode_label(mode, custom_mode=custom_mode)
    blocked_total = int(blocked_entries_total or 0)

    if mode == MODE_NOTHING_SPECIAL:
        effective = False
        note = "Nothing Special selected: earnings filter is inactive for this run."
    elif dates_count == 0:
        effective = False
        note = "No earnings dates returned by Yahoo for this ticker/date window, so earnings filtering could not be applied."
    elif blocked_total > 0:
        effective = True
        suffix = "signal" if blocked_total == 1 else "signals"
        note = f"Earnings filter active: blocked {blocked_total} candidate entry {suffix}."
    else:
        effective = True
        note = "Earnings filter active, but no strategy entry signals landed inside the blackout windows."

    payload.update({
        "mode_label": mode_label,
        "dates_count": dates_count,
        "blocked_entry_signals_total": blocked_total,
        "window_label": f"{before_days}d before / {after_days}d after",
        "effective": effective,
        "note": note,
    })
    return payload


def ensure_strategy_definitions() -> list[StrategyDefinition]:
    definitions: list[StrategyDefinition] = []
    for strategy in get_supported_strategies():
        definition, _ = StrategyDefinition.objects.update_or_create(
            slug=strategy.slug,
            defaults={
                "name": strategy.name,
                "category": strategy.category,
                "description": strategy.description,
                "is_active": True,
                "default_params": strategy.default_params,
            },
        )
        definitions.append(definition)
    return definitions


def list_strategy_definitions() -> list[dict]:
    ensure_strategy_definitions()
    definitions_by_slug = {definition.slug: definition for definition in StrategyDefinition.objects.filter(is_active=True)}
    ordered = []
    for strategy in get_supported_strategies():
        definition = definitions_by_slug[strategy.slug]
        ordered.append({
            "slug": definition.slug,
            "name": definition.name,
            "category": definition.category,
            "description": definition.description,
            "default_params": definition.default_params,
        })
    return ordered


def _parse_date(raw_value: str, label: str) -> date:
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must use YYYY-MM-DD format.") from error


def _normalize_strategy_chain(strategy_chain: list[dict], analysis_mode: str) -> list[dict]:
    if not isinstance(strategy_chain, list) or not strategy_chain:
        raise ValueError("At least one strategy must be configured.")

    if analysis_mode == BacktestRun.ANALYSIS_MODE_SINGLE and len(strategy_chain) != 1:
        raise ValueError("Single Strategy Analysis accepts exactly one strategy.")

    normalized: list[dict] = []
    seen_slugs: set[str] = set()

    for item in strategy_chain:
        if not isinstance(item, dict):
            raise ValueError("Each strategy entry must be an object with slug and params.")

        slug = (item.get("slug") or "").strip()
        if not slug:
            raise ValueError("Each strategy entry requires a slug.")
        if slug in seen_slugs:
            raise ValueError("Duplicate strategies are not allowed in one run.")

        strategy = get_strategy(slug)
        params = strategy.normalize_params(item.get("params") or {})
        normalized.append({
            "slug": slug,
            "params": params,
        })
        seen_slugs.add(slug)

    return normalized


def _validate_request_payload(payload: dict) -> dict:
    analysis_mode = (payload.get("analysis_mode") or BacktestRun.ANALYSIS_MODE_SINGLE).strip()
    prior_mode = (payload.get("prior_mode") or BacktestRun.PRIOR_MODE_UNIVERSE).strip()
    ticker = (payload.get("ticker") or "").upper().strip()
    benchmark = (payload.get("benchmark") or "SPY").upper().strip()
    start_date_raw = payload.get("start_date")
    end_date_raw = payload.get("end_date")
    horizon_days = int(payload.get("horizon_days") or 126)
    earnings_config = normalize_earnings_config(payload.get("earnings") or {})

    if not ticker:
        raise ValueError("Ticker is required.")
    if analysis_mode not in SUPPORTED_ANALYSIS_MODES:
        raise ValueError("Unsupported analysis mode.")
    if prior_mode not in SUPPORTED_PRIOR_MODES:
        raise ValueError("Unsupported prior mode.")
    if horizon_days <= 0:
        raise ValueError("Horizon days must be greater than zero.")

    start_date = _parse_date(start_date_raw, "Start date")
    end_date = _parse_date(end_date_raw, "End date")
    if start_date > end_date:
        raise ValueError("Start date must be on or before end date.")

    strategy_chain = _normalize_strategy_chain(payload.get("strategy_chain") or [], analysis_mode)

    return {
        "ticker": ticker,
        "start_date": start_date,
        "end_date": end_date,
        "analysis_mode": analysis_mode,
        "prior_mode": prior_mode,
        "benchmark": benchmark or "SPY",
        "horizon_days": horizon_days,
        "strategy_chain": strategy_chain,
        "earnings": earnings_config,
    }


def _serialize_trade_model(trade: TradeLog) -> dict:
    return {
        "strategy_slug": trade.strategy_slug,
        "sequence_index": trade.sequence_index,
        "entry_date": trade.entry_date.isoformat(),
        "exit_date": trade.exit_date.isoformat() if trade.exit_date else None,
        "entry_price": float(trade.entry_price),
        "exit_price": float(trade.exit_price) if trade.exit_price is not None else None,
        "shares": float(trade.shares),
        "pnl": float(trade.pnl) if trade.pnl is not None else None,
        "return_pct": float(trade.return_pct) if trade.return_pct is not None else None,
        "outcome": trade.outcome,
    }


def _serialize_strategy_run(strategy_run: StrategyRun) -> dict:
    evidence_payload = strategy_run.evidence_json or {}
    return {
        "slug": strategy_run.strategy.slug,
        "name": strategy_run.strategy.name,
        "sequence_index": strategy_run.sequence_index,
        "params": strategy_run.params,
        "active": bool(strategy_run.signal_active),
        "used_as_prior": bool(strategy_run.used_as_prior),
        "strength": float(strategy_run.strength_score or 0.0),
        "likelihood_ratio": float(strategy_run.likelihood_ratio or 1.0),
        "weighted_log_lr": float(strategy_run.weighted_log_lr or 0.0),
        "posterior_after": float(strategy_run.posterior_after or 0.0),
        "metrics": strategy_run.metrics,
        "blocked_entry_signals": int(evidence_payload.get("earnings_blocked_entries", 0)),
        "evidence": evidence_payload,
    }


def _build_prior_math(prior_source: dict, prior_mode: str) -> dict:
    support = prior_source.get("support", {})
    observed_event = support.get("observed_event")
    is_conditional = prior_mode == BacktestRun.PRIOR_MODE_GOLDEN_CROSS

    if is_conditional:
        formula = "prior = (successes + alpha) / (total + 2 * alpha), conditioned on the observed Golden Cross state"
        condition_text = "Golden Cross active" if observed_event else "Golden Cross inactive"
        label = "Golden Cross Prior"
    else:
        formula = "prior = (successes + alpha) / (total + 2 * alpha)"
        condition_text = "Universe-wide historical success baseline"
        label = "Universe Prior"

    return {
        "label": label,
        "mode": prior_source.get("mode") or prior_mode,
        "probability": float(prior_source.get("probability", 0.5)),
        "probability_pct": float(prior_source.get("probability", 0.5)) * 100.0,
        "alpha": float(prior_source.get("alpha", 1.0)),
        "support": support,
        "observed_event": observed_event,
        "condition_text": condition_text,
        "formula": formula,
        "display_rows": [
            {"label": "Successes", "value": int(support.get("successes", 0))},
            {"label": "Total observations", "value": int(support.get("total", 0))},
            {"label": "Alpha", "value": float(prior_source.get("alpha", 1.0))},
        ],
    }


def _build_math_payload(
    backtest_run: BacktestRun,
    prior_source: dict,
    evidence_items: list[dict],
    final_probability: float,
) -> dict:
    return {
        "prior": _build_prior_math(prior_source, backtest_run.prior_mode),
        "steps": [
            {
                "sequence_index": int(item["sequence_index"]),
                "slug": item["slug"],
                "name": item["name"],
                "used_as_prior": bool(item["used_as_prior"]),
                "signal_active": bool(item["signal_active"]),
                "observed_event": bool(item["observed_event"]),
                "strength": float(item["strength"]),
                "strength_pct": float(item["strength"]) * 100.0,
                "prior_before": float(item["prior_before"]),
                "prior_before_pct": float(item["prior_before"]) * 100.0,
                "prior_log_odds": float(item["prior_log_odds"]),
                "probability_given_success": float(item["probability_given_success"]),
                "probability_given_success_pct": float(item["probability_given_success"]) * 100.0,
                "probability_given_failure": float(item["probability_given_failure"]),
                "probability_given_failure_pct": float(item["probability_given_failure"]) * 100.0,
                "likelihood_alpha": float(item["likelihood_alpha"]),
                "likelihood_ratio": float(item["likelihood_ratio"]),
                "log_likelihood_ratio": float(item["log_likelihood_ratio"]),
                "weight": float(item["weight"]),
                "weighted_log_lr": float(item["weighted_log_lr"]),
                "posterior_after": float(item["posterior_after"]),
                "posterior_after_pct": float(item["posterior_after"]) * 100.0,
                "posterior_log_odds": float(item["posterior_log_odds"]),
                "support": item["support"],
                "signal_math": item["signal_math"],
            }
            for item in evidence_items
        ],
        "final": {
            "prior_probability": float(backtest_run.prior_value),
            "prior_probability_pct": float(backtest_run.prior_value) * 100.0,
            "posterior_probability": float(final_probability),
            "posterior_probability_pct": float(final_probability) * 100.0,
            "bayesian_lift": float(final_probability - backtest_run.prior_value),
            "bayesian_lift_pct": float(final_probability - backtest_run.prior_value) * 100.0,
            "confidence_label": confidence_label(final_probability),
        },
        "glossary": BAYES_GLOSSARY,
    }


def serialize_backtest_run(backtest_run: BacktestRun) -> dict:
    strategy_runs = list(backtest_run.strategy_runs.select_related("strategy").all())
    trades = list(backtest_run.trades.all())
    snapshot = getattr(backtest_run, "evidence_snapshot", None)
    evidence_payload = snapshot.evidence_json if snapshot else {}
    equity_curve = evidence_payload.get("equity_curve", []) if snapshot else []

    earnings_payload = _enrich_earnings_payload(
        backtest_run.request_payload.get("earnings") or {},
        sum(
        int((strategy_run.evidence_json or {}).get("earnings_blocked_entries", 0))
        for strategy_run in strategy_runs
        ),
    )

    return {
        "run_id": backtest_run.id,
        "ticker": backtest_run.ticker,
        "start_date": backtest_run.start_date.isoformat(),
        "end_date": backtest_run.end_date.isoformat(),
        "analysis_mode": backtest_run.analysis_mode,
        "prior_mode": backtest_run.prior_mode,
        "horizon_days": backtest_run.horizon_days,
        "benchmark": backtest_run.benchmark,
        "prior_probability": float(backtest_run.prior_value),
        "posterior_probability": float(backtest_run.posterior_value or backtest_run.prior_value),
        "confidence_label": confidence_label(backtest_run.posterior_value or backtest_run.prior_value),
        "strategies": [_serialize_strategy_run(strategy_run) for strategy_run in strategy_runs],
        "trade_log": [_serialize_trade_model(trade) for trade in trades],
        "explanation": snapshot.explanation_json if snapshot else {},
        "evidence": evidence_payload if snapshot else {},
        "math": evidence_payload.get("math", {}) if snapshot else {},
        "equity_curve": equity_curve,
        "earnings": earnings_payload,
        "ui": {
            "can_add_another_strategy": backtest_run.analysis_mode == BacktestRun.ANALYSIS_MODE_MULTI
            and len(strategy_runs) < len(get_supported_strategies()),
            "completed_steps": len(strategy_runs),
        },
    }


def run_bayesian_backtest(payload: dict, user=None) -> dict:
    ensure_strategy_definitions()
    request_data = _validate_request_payload(payload)

    ticker = request_data["ticker"]
    start_date_iso = request_data["start_date"].isoformat()
    end_date_iso = request_data["end_date"].isoformat()
    analysis_mode = request_data["analysis_mode"]
    prior_mode = request_data["prior_mode"]
    benchmark = request_data["benchmark"]
    horizon_days = request_data["horizon_days"]
    strategy_chain = request_data["strategy_chain"]
    requested_earnings_config = request_data["earnings"]

    earnings_config = (
        requested_earnings_config
        if requested_earnings_config.get("mode") == MODE_NOTHING_SPECIAL
        else resolve_earnings_config(
            requested_earnings_config,
            ticker=ticker,
            start_date=request_data["start_date"],
            end_date=request_data["end_date"],
        )
    )
    runtime_context = {
        "earnings_filter": earnings_config,
    }

    feature_frame = load_feature_frame(ticker, start_date_iso, end_date_iso, benchmark=benchmark, horizon_days=horizon_days)
    training_frames, training_symbols, training_errors = load_training_frames(
        build_training_universe(ticker, benchmark),
        start_date_iso,
        end_date_iso,
        benchmark=benchmark,
        horizon_days=horizon_days,
    )

    universe_prior = estimate_universe_prior(training_frames)
    prior_probability = universe_prior["probability"]
    prior_source = universe_prior

    golden_cross_observed = None
    if prior_mode == BacktestRun.PRIOR_MODE_GOLDEN_CROSS:
        golden_cross_chain = next((item for item in strategy_chain if item["slug"] == "golden_cross"), None)
        golden_cross_strategy = get_strategy("golden_cross")
        golden_cross_params = golden_cross_strategy.normalize_params(golden_cross_chain["params"] if golden_cross_chain else {})
        golden_cross_frame = golden_cross_strategy.compute_features(feature_frame.copy(), golden_cross_params)
        golden_cross_signal = golden_cross_strategy.generate_signal(golden_cross_frame, golden_cross_params).fillna(False).astype(bool)
        golden_cross_entry_allowed = golden_cross_strategy.entry_allowed_mask(golden_cross_frame, runtime_context)
        golden_cross_signal = golden_cross_signal & golden_cross_entry_allowed
        golden_cross_observed = golden_cross_strategy.latest_boolean(golden_cross_signal)
        prior_source = estimate_conditional_prior(
            golden_cross_strategy,
            training_frames,
            golden_cross_params,
            golden_cross_observed,
        )
        prior_probability = prior_source["probability"]

    strategy_definitions = {definition.slug: definition for definition in StrategyDefinition.objects.filter(is_active=True)}
    current_probability = prior_probability
    evidence_items: list[dict] = []
    aggregated_trades: list[dict] = []
    aggregated_equity_curve: list[dict] = []
    previous_signals = []
    golden_cross_prior_consumed = False

    with transaction.atomic():
        backtest_run = BacktestRun.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            ticker=ticker,
            start_date=request_data["start_date"],
            end_date=request_data["end_date"],
            horizon_days=horizon_days,
            analysis_mode=analysis_mode,
            prior_mode=prior_mode,
            prior_value=prior_probability,
            benchmark=benchmark,
            status=BacktestRun.STATUS_COMPLETED,
            request_payload={
                "ticker": ticker,
                "start_date": start_date_iso,
                "end_date": end_date_iso,
                "analysis_mode": analysis_mode,
                "prior_mode": prior_mode,
                "benchmark": benchmark,
                "horizon_days": horizon_days,
                "strategy_chain": strategy_chain,
                "earnings": earnings_config,
                "training_symbols": training_symbols,
                "training_errors": training_errors,
            },
        )

        for index, chain_entry in enumerate(strategy_chain, start=1):
            strategy = get_strategy(chain_entry["slug"])
            params = strategy.normalize_params(chain_entry["params"])
            strategy_frame = strategy.compute_features(feature_frame.copy(), params)
            signal_series = strategy.generate_signal(strategy_frame, params).fillna(False).astype(bool)
            entry_allowed_mask = strategy.entry_allowed_mask(strategy_frame, runtime_context)
            filtered_signal_series = signal_series & entry_allowed_mask
            blocked_entry_signals = int((signal_series & (~entry_allowed_mask)).sum())
            strength_series = strategy.signal_strength(strategy_frame, params)
            observed_event = strategy.latest_boolean(filtered_signal_series)
            likelihood = estimate_binary_likelihood(filtered_signal_series, strategy_frame["target_success"], observed_event)
            weight = estimate_signal_weight(filtered_signal_series, previous_signals)
            prior_before = current_probability
            prior_log_odds = probability_to_log_odds(prior_before)
            signal_math = strategy.describe_signal_math(strategy_frame, params, filtered_signal_series, strength_series)
            used_as_prior = (
                prior_mode == BacktestRun.PRIOR_MODE_GOLDEN_CROSS
                and strategy.slug == "golden_cross"
                and not golden_cross_prior_consumed
            )
            if used_as_prior:
                posterior_after = current_probability
                weighted_log_lr = 0.0
                golden_cross_prior_consumed = True
            else:
                posterior_after, weighted_log_lr = apply_evidence(
                    prior_before,
                    likelihood["likelihood_ratio"],
                    weight=weight,
                )
                current_probability = posterior_after
            posterior_log_odds = probability_to_log_odds(posterior_after)

            backtest_result = strategy.backtest(
                strategy_frame,
                params,
                runtime_context={
                    **runtime_context,
                    "entry_allowed_mask": entry_allowed_mask,
                },
            )
            aggregated_trades.extend([
                {
                    **trade,
                    "sequence_index": index,
                }
                for trade in backtest_result["trades"]
            ])
            if backtest_result["equity_curve"]:
                aggregated_equity_curve = backtest_result["equity_curve"]

            evidence_item = {
                "slug": strategy.slug,
                "name": strategy.name,
                "sequence_index": index,
                "params": params,
                "signal_active": observed_event,
                "strength": strategy.latest_float(strength_series),
                "prior_before": prior_before,
                "prior_log_odds": prior_log_odds,
                "likelihood_ratio": likelihood["likelihood_ratio"],
                "log_likelihood_ratio": likelihood["log_likelihood_ratio"],
                "probability_given_success": likelihood["probability_given_success"],
                "probability_given_failure": likelihood["probability_given_failure"],
                "likelihood_alpha": likelihood["alpha"],
                "weighted_log_lr": weighted_log_lr,
                "posterior_after": posterior_after,
                "posterior_log_odds": posterior_log_odds,
                "used_as_prior": used_as_prior,
                "weight": weight,
                "support": likelihood["support"],
                "observed_event": likelihood["observed_event"],
                "metrics": backtest_result["metrics"],
                "earnings_blocked_entries": blocked_entry_signals,
                "signal_math": signal_math,
            }
            evidence_items.append(evidence_item)

            StrategyRun.objects.create(
                backtest_run=backtest_run,
                strategy=strategy_definitions[strategy.slug],
                sequence_index=index,
                params=params,
                signal_active=observed_event,
                used_as_prior=used_as_prior,
                strength_score=evidence_item["strength"],
                likelihood_ratio=evidence_item["likelihood_ratio"],
                weighted_log_lr=evidence_item["weighted_log_lr"],
                posterior_after=evidence_item["posterior_after"],
                metrics=backtest_result["metrics"],
                evidence_json={
                    "weight": weight,
                    "observed_event": likelihood["observed_event"],
                    "support": likelihood["support"],
                    "probability_given_success": likelihood["probability_given_success"],
                    "probability_given_failure": likelihood["probability_given_failure"],
                    "likelihood_alpha": likelihood["alpha"],
                    "log_likelihood_ratio": likelihood["log_likelihood_ratio"],
                    "prior_before": prior_before,
                    "prior_log_odds": prior_log_odds,
                    "posterior_log_odds": posterior_log_odds,
                    "earnings_blocked_entries": blocked_entry_signals,
                    "signal_math": signal_math,
                },
            )

            for trade in backtest_result["trades"]:
                TradeLog.objects.create(
                    backtest_run=backtest_run,
                    strategy_slug=strategy.slug,
                    sequence_index=index,
                    entry_date=date.fromisoformat(trade["entry_date"]),
                    exit_date=date.fromisoformat(trade["exit_date"]) if trade.get("exit_date") else None,
                    entry_price=trade["entry_price"],
                    exit_price=trade.get("exit_price"),
                    shares=trade["shares"],
                    pnl=trade.get("pnl"),
                    return_pct=trade.get("return_pct"),
                    outcome=trade.get("outcome", ""),
                )

            if not used_as_prior:
                previous_signals.append(filtered_signal_series)

        explanation = build_backtest_explanation(
            prior_probability,
            current_probability,
            evidence_items,
            prior_mode,
            analysis_mode,
        )
        math_payload = _build_math_payload(backtest_run, prior_source, evidence_items, current_probability)

        EvidenceSnapshot.objects.create(
            backtest_run=backtest_run,
            prior_probability=prior_probability,
            posterior_probability=current_probability,
            evidence_json={
                "prior_source": prior_source,
                "strategies": evidence_items,
                "equity_curve": aggregated_equity_curve,
                "math": math_payload,
            },
            explanation_json=explanation,
        )

        backtest_run.posterior_value = current_probability
        backtest_run.save(update_fields=["posterior_value"])

    earnings_response = _enrich_earnings_payload(
        earnings_config,
        sum(
        int(item.get("earnings_blocked_entries", 0))
        for item in evidence_items
        ),
    )

    return {
        **serialize_backtest_run(backtest_run),
        "equity_curve": aggregated_equity_curve,
        "earnings": earnings_response,
        "ui": {
            "can_add_another_strategy": analysis_mode == BacktestRun.ANALYSIS_MODE_MULTI
            and len(strategy_chain) < len(get_supported_strategies()),
            "completed_steps": len(strategy_chain),
            "next_sequence_index": len(strategy_chain) + 1,
            "workflow_note": (
                "Posterior established. Add another strategy to continue the Bayesian chain."
                if analysis_mode == BacktestRun.ANALYSIS_MODE_MULTI and len(strategy_chain) < len(get_supported_strategies())
                else "Current strategy chain is complete for this run."
            ),
        },
    }
