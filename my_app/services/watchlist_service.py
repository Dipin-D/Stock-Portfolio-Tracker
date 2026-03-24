from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from django.core.cache import cache
from django.utils import timezone

from my_app.data.universe import get_watchlist_universe
from my_app.strategies import get_strategy
from my_app.utils import download_n_clean_data


WATCHLIST_REFRESH_SECONDS = 300
WATCHLIST_TIMEZONE = "America/New_York"
MOMENTUM_CACHE_VERSION = 1
GOLDEN_CROSS_CACHE_VERSION = 2
GOLDEN_CROSS_WEIGHTED_CACHE_VERSION = 1
GOLDEN_CROSS_SYMBOL_CACHE_VERSION = 1
LIVE_GOLDEN_CROSS_STRONG_THRESHOLD = 70.0
WEIGHTED_GOLDEN_CROSS_STRONG_THRESHOLD = 70.0

GOLDEN_CROSS_COMPOSITE_FORMULA = {
    "title": "Golden Cross Composite Score",
    "formula": "100 * (0.30 * recency_score + 0.25 * spread_score + 0.20 * slope_score + 0.15 * price_confirmation + 0.10 * volume_confirmation)",
    "components": [
        {
            "label": "Recency Score",
            "formula": "clamp(1 - bars_since_last_cross_up / 120, 0, 1)",
            "weight": 0.30,
            "normalizer": "120 bars",
        },
        {
            "label": "Spread Score",
            "formula": "clamp(((sma_50 - sma_200) / sma_200) / 0.12, 0, 1)",
            "weight": 0.25,
            "normalizer": "12% spread",
        },
        {
            "label": "Slope Score",
            "formula": "0.5 * clamp((sma_50 / sma_50_20bars_ago - 1) / 0.06, 0, 1) + 0.5 * clamp((sma_200 / sma_200_20bars_ago - 1) / 0.03, 0, 1)",
            "weight": 0.20,
            "normalizer": "6% fast slope, 3% slow slope",
        },
        {
            "label": "Price Confirmation",
            "formula": "0.5 * clamp((close / sma_50 - 1) / 0.08, 0, 1) + 0.5 * clamp((close / sma_200 - 1) / 0.12, 0, 1)",
            "weight": 0.15,
            "normalizer": "8% above fast SMA, 12% above slow SMA",
        },
        {
            "label": "Volume Confirmation",
            "formula": "clamp((latest_volume / avg_volume_20 - 1) / 0.75, 0, 1)",
            "weight": 0.10,
            "normalizer": "0.75 above average volume ratio",
        },
    ],
}

GOLDEN_CROSS_WEIGHTED_FORMULA = {
    "title": "Golden Cross Weighted Backtest Score",
    "formula": "100 * (0.30 * win_rate_score + 0.20 * avg_trade_return_score + 0.25 * total_return_score + 0.15 * drawdown_score + 0.10 * trade_count_score)",
    "components": [
        {
            "label": "Win Rate Score",
            "formula": "clamp(win_rate / 0.70, 0, 1)",
            "weight": 0.30,
            "normalizer": "70% win rate",
        },
        {
            "label": "Average Trade Return Score",
            "formula": "clamp(avg_trade_return / 0.15, 0, 1)",
            "weight": 0.20,
            "normalizer": "15% average trade return",
        },
        {
            "label": "Total Return Score",
            "formula": "clamp(total_return_pct / 2.00, 0, 1)",
            "weight": 0.25,
            "normalizer": "200% total return",
        },
        {
            "label": "Drawdown Score",
            "formula": "1 - clamp(abs(max_drawdown) / 0.50, 0, 1)",
            "weight": 0.15,
            "normalizer": "50% max drawdown",
        },
        {
            "label": "Trade Count Score",
            "formula": "clamp(trade_count / 12, 0, 1)",
            "weight": 0.10,
            "normalizer": "12 completed trades",
        },
    ],
}


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(float(value), upper))


def _now_est() -> datetime:
    return datetime.now(ZoneInfo(WATCHLIST_TIMEZONE))


def _format_as_of() -> str:
    return _now_est().strftime("%Y-%m-%d %H:%M")


def _research_url(symbol: str) -> str:
    return f"/research/{symbol.upper()}/"


def _research_url_with_source(
    symbol: str,
    source_list: str,
    source_rank: int,
    source_score: float,
    source_signal: str,
) -> str:
    return (
        f"/research/{symbol.upper()}/"
        f"?source_list={source_list.replace(' ', '%20')}"
        f"&source_rank={source_rank}"
        f"&source_score={source_score:.2f}"
        f"&source_signal={source_signal}"
    )


def _math_url(signal: str, symbol: str) -> str:
    return f"/theMath/?section=watchlist_signals&signal={signal}&ticker={symbol.upper()}#watchlist-signals"


def _normalize_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    if "Date" not in normalized.columns:
        normalized = normalized.reset_index()

    normalized["Date_dt"] = pd.to_datetime(normalized["Date"], unit="s", errors="coerce")
    normalized = normalized.dropna(subset=["Date_dt"]).sort_values("Date_dt").reset_index(drop=True)
    return normalized


def _weighted_backtest_window() -> tuple[str, str]:
    today = timezone.localdate()
    start = today - timedelta(days=3652)
    return start.isoformat(), today.isoformat()


def _consensus_label(live_score: float | None, quality_score: float | None) -> str:
    live_strong = float(live_score or 0.0) >= LIVE_GOLDEN_CROSS_STRONG_THRESHOLD
    history_strong = float(quality_score or 0.0) >= WEIGHTED_GOLDEN_CROSS_STRONG_THRESHOLD

    if live_strong and history_strong:
        return "Strong Now + Strong History"
    if live_strong and not history_strong:
        return "Strong Now + Weak History"
    if not live_strong and history_strong:
        return "Weak Now + Strong History"
    return "Weak Now + Weak History"


def _consensus_note(consensus_label: str) -> str:
    notes = {
        "Strong Now + Strong History": "The current crossover structure is strong and the historical Golden Cross profile is also strong.",
        "Strong Now + Weak History": "The live crossover looks strong, but the 10-year Golden Cross backtest quality is weaker than the current setup suggests.",
        "Weak Now + Strong History": "The ticker has historically strong Golden Cross behavior, but the current live crossover structure is not strong right now.",
        "Weak Now + Weak History": "Neither the current crossover structure nor the historical Golden Cross behavior is strong right now.",
    }
    return notes[consensus_label]


def get_golden_cross_consensus_label(live_score: float | None, quality_score: float | None) -> str:
    return _consensus_label(live_score, quality_score)


def build_watchlist_math_url(signal: str, symbol: str) -> str:
    return _math_url(signal, symbol)


def _build_weighted_quality_components(metrics: dict) -> dict:
    win_rate = float(metrics.get("win_rate", 0.0))
    avg_trade_return = float(metrics.get("avg_trade_return", 0.0))
    total_return_pct = float(metrics.get("total_return_pct", 0.0))
    max_drawdown = float(metrics.get("max_drawdown", 0.0))
    trade_count = int(metrics.get("trade_count", 0))

    win_rate_score = _clamp(win_rate / 0.70)
    avg_trade_return_score = _clamp(avg_trade_return / 0.15)
    total_return_score = _clamp(total_return_pct / 2.00)
    drawdown_score = 1.0 - _clamp(abs(max_drawdown) / 0.50)
    trade_count_score = _clamp(trade_count / 12.0)

    quality_score = 100.0 * (
        0.30 * win_rate_score +
        0.20 * avg_trade_return_score +
        0.25 * total_return_score +
        0.15 * drawdown_score +
        0.10 * trade_count_score
    )

    return {
        "win_rate_score": round(float(win_rate_score), 4),
        "avg_trade_return_score": round(float(avg_trade_return_score), 4),
        "total_return_score": round(float(total_return_score), 4),
        "drawdown_score": round(float(drawdown_score), 4),
        "trade_count_score": round(float(trade_count_score), 4),
        "quality_score": round(float(quality_score), 2),
    }


def _ref_window_for_lookback(max_lookback: int) -> tuple[str, str, datetime.date]:
    today = _now_est().date()
    ref_date = today - timedelta(days=30)
    start = ref_date - timedelta(days=(max_lookback * 2 + 10))
    return start.isoformat(), ref_date.isoformat(), ref_date


def _one_day_momentum(df: pd.DataFrame, lookback: int, ref_date) -> float | None:
    if df is None or df.empty or "Close" not in df:
        return None

    normalized = _normalize_price_frame(df)
    df_cut = normalized.loc[normalized["Date_dt"] <= pd.Timestamp(ref_date)]
    if df_cut.empty or len(df_cut) <= lookback:
        return None

    close = pd.to_numeric(df_cut["Close"], errors="coerce").dropna()
    if len(close) <= lookback:
        return None

    current_close = float(close.iloc[-1])
    past_close = float(close.iloc[-1 - lookback])
    if current_close <= 0 or past_close <= 0:
        return None

    return (current_close / past_close) - 1.0


def get_momentum_watchlist() -> dict:
    cache_key = f"watchlist:momentum:v{MOMENTUM_CACHE_VERSION}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    presets = [("mom-60", 60), ("mom-120", 120)]
    max_lookback = max(lookback for _, lookback in presets)
    start_iso, end_iso, ref_date = _ref_window_for_lookback(max_lookback)

    payload: dict[str, list[dict]] = {}
    for key, lookback in presets:
        rows: list[dict] = []
        for symbol in get_watchlist_universe():
            try:
                frame = download_n_clean_data(symbol, start_iso, end_iso, compute_sma=False)
                momentum = _one_day_momentum(frame, lookback, ref_date)
                if momentum is None:
                    continue
                rows.append({
                    "symbol": symbol,
                    "momentum_pct": float(momentum * 100.0),
                    "research_url": _research_url(symbol),
                })
            except Exception:
                continue

        rows.sort(key=lambda row: row["momentum_pct"], reverse=True)
        payload[key] = rows[:5]

    response = {
        "valid": True,
        "start": start_iso,
        "end": end_iso,
        "ref_date": ref_date.isoformat(),
        "as_of": _format_as_of(),
        "refresh_seconds": WATCHLIST_REFRESH_SECONDS,
        "results": payload,
    }
    cache.set(cache_key, response, WATCHLIST_REFRESH_SECONDS)
    return response


def compute_golden_cross_snapshot(frame: pd.DataFrame, require_active: bool = False) -> dict | None:
    if frame is None or frame.empty:
        return None

    normalized = _normalize_price_frame(frame)
    if "sma_50" not in normalized.columns:
        normalized["sma_50"] = normalized["Close"].rolling(50).mean()
    if "sma_200" not in normalized.columns:
        normalized["sma_200"] = normalized["Close"].rolling(200).mean()

    normalized["avg_volume_20"] = normalized["Volume"].rolling(20).mean()
    valid = normalized.dropna(subset=["sma_50", "sma_200", "Close", "Volume", "avg_volume_20"]).reset_index(drop=True)
    if len(valid) < 21:
        return None

    active = (valid["sma_50"] > valid["sma_200"]).astype(bool)
    is_active = bool(active.iloc[-1])
    if require_active and not is_active:
        return None

    active_values = active.to_numpy(dtype=bool)
    cross_up = active_values & ~np.roll(active_values, 1)
    cross_up[0] = active_values[0]
    cross_positions = np.flatnonzero(cross_up)
    last_cross_position = int(cross_positions[-1]) if cross_positions.size else None
    latest_position = len(valid) - 1
    bars_since_cross = (latest_position - last_cross_position) if last_cross_position is not None else latest_position

    latest = valid.iloc[-1]
    lookback_20 = valid.iloc[-21] if len(valid) > 20 else valid.iloc[0]
    sma_50 = float(latest["sma_50"])
    sma_200 = float(latest["sma_200"])
    latest_close = float(latest["Close"])
    latest_volume = float(latest["Volume"])
    avg_volume_20 = float(latest["avg_volume_20"]) if pd.notna(latest["avg_volume_20"]) else 0.0
    spread_ratio = ((sma_50 - sma_200) / sma_200) if sma_200 else 0.0
    price_above_sma200 = ((latest_close / sma_200) - 1.0) if sma_200 else 0.0
    price_above_sma50 = ((latest_close / sma_50) - 1.0) if sma_50 else 0.0
    volume_ratio = (latest_volume / avg_volume_20) if avg_volume_20 else 0.0
    lookback_sma_50 = float(lookback_20["sma_50"]) if pd.notna(lookback_20["sma_50"]) else 0.0
    lookback_sma_200 = float(lookback_20["sma_200"]) if pd.notna(lookback_20["sma_200"]) else 0.0
    slope_50 = ((sma_50 / lookback_sma_50) - 1.0) if lookback_sma_50 else 0.0
    slope_200 = ((sma_200 / lookback_sma_200) - 1.0) if lookback_sma_200 else 0.0

    recency_score = _clamp(1.0 - (bars_since_cross / 120.0))
    spread_score = _clamp(spread_ratio / 0.12)
    slope_score = (
        0.5 * _clamp(slope_50 / 0.06) +
        0.5 * _clamp(slope_200 / 0.03)
    )
    price_confirmation = (
        0.5 * _clamp(price_above_sma50 / 0.08) +
        0.5 * _clamp(price_above_sma200 / 0.12)
    )
    volume_confirmation = _clamp((volume_ratio - 1.0) / 0.75)

    composite_score = 100.0 * (
        0.30 * recency_score +
        0.25 * spread_score +
        0.20 * slope_score +
        0.15 * price_confirmation +
        0.10 * volume_confirmation
    )
    if not is_active:
        composite_score = 0.0

    last_cross_date = None
    if last_cross_position is not None:
        last_cross_date = valid.iloc[last_cross_position]["Date_dt"].date()

    latest_date = latest["Date_dt"].date()
    days_since_cross = (latest_date - last_cross_date).days if last_cross_date else None

    return {
        "is_active": is_active,
        "composite_score": round(float(composite_score), 2),
        "bars_since_cross": int(bars_since_cross),
        "days_since_cross": int(days_since_cross) if days_since_cross is not None else None,
        "last_cross_date": last_cross_date.isoformat() if last_cross_date else None,
        "as_of_date": latest_date.isoformat(),
        "spread_pct": round(float(spread_ratio * 100.0), 2),
        "price_above_sma200_pct": round(float(price_above_sma200 * 100.0), 2),
        "price_above_sma50_pct": round(float(price_above_sma50 * 100.0), 2),
        "volume_ratio": round(float(volume_ratio), 2),
        "latest_close": round(latest_close, 2),
        "sma_50": round(sma_50, 2),
        "sma_200": round(sma_200, 2),
        "component_scores": {
            "recency_score": round(float(recency_score), 4),
            "spread_score": round(float(spread_score), 4),
            "slope_score": round(float(slope_score), 4),
            "price_confirmation": round(float(price_confirmation), 4),
            "volume_confirmation": round(float(volume_confirmation), 4),
        },
    }


def compute_golden_cross_weighted_snapshot(frame: pd.DataFrame) -> dict | None:
    if frame is None or frame.empty:
        return None

    normalized = _normalize_price_frame(frame)
    if normalized.empty:
        return None

    strategy = get_strategy("golden_cross")
    params = strategy.normalize_params(strategy.default_params)
    strategy_frame = strategy.compute_features(normalized.copy(), params)
    backtest = strategy.backtest(strategy_frame, params)
    metrics = backtest.get("metrics", {})
    score_components = _build_weighted_quality_components(metrics)
    start_date, end_date = _weighted_backtest_window()

    return {
        "quality_score": score_components["quality_score"],
        "win_rate": float(metrics.get("win_rate", 0.0)),
        "avg_trade_return": float(metrics.get("avg_trade_return", 0.0)),
        "total_return_pct": float(metrics.get("total_return_pct", 0.0)),
        "max_drawdown": float(metrics.get("max_drawdown", 0.0)),
        "trade_count": int(metrics.get("trade_count", 0)),
        "wins": int(metrics.get("wins", 0)),
        "losses": int(metrics.get("losses", 0)),
        "score_components": score_components,
        "window": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "starting_cash": float(metrics.get("starting_cash", 100000.0)),
        "final_cash": float(metrics.get("final_cash", 100000.0)),
    }


def get_live_golden_cross_snapshot(symbol: str, require_active: bool = False) -> dict | None:
    normalized_symbol = symbol.upper().strip()
    cache_key = f"watchlist:golden_cross:symbol:{normalized_symbol}:active{int(require_active)}:v{GOLDEN_CROSS_SYMBOL_CACHE_VERSION}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    today = timezone.localdate()
    start_date = (today - timedelta(days=900)).isoformat()
    snapshot = None
    try:
        frame = download_n_clean_data(normalized_symbol, start_date, today.isoformat(), compute_sma=True)
        snapshot = compute_golden_cross_snapshot(frame, require_active=require_active)
    except Exception:
        snapshot = None

    cache.set(cache_key, snapshot, WATCHLIST_REFRESH_SECONDS)
    return snapshot


def get_weighted_golden_cross_snapshot(symbol: str) -> dict | None:
    normalized_symbol = symbol.upper().strip()
    cache_key = f"watchlist:golden_cross:weighted:symbol:{normalized_symbol}:v{GOLDEN_CROSS_SYMBOL_CACHE_VERSION}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    start_date, end_date = _weighted_backtest_window()
    snapshot = None
    try:
        frame = download_n_clean_data(normalized_symbol, start_date, end_date, compute_sma=False)
        snapshot = compute_golden_cross_weighted_snapshot(frame)
    except Exception:
        snapshot = None

    cache.set(cache_key, snapshot, WATCHLIST_REFRESH_SECONDS)
    return snapshot


def get_golden_cross_watchlist() -> dict:
    cache_key = f"watchlist:golden_cross:v{GOLDEN_CROSS_CACHE_VERSION}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    today = timezone.localdate()
    start_date = (today - timedelta(days=900)).isoformat()
    end_date = today.isoformat()

    rows: list[dict] = []
    for symbol in get_watchlist_universe():
        try:
            snapshot = get_live_golden_cross_snapshot(symbol, require_active=True)
            if not snapshot:
                continue

            weighted_snapshot = get_weighted_golden_cross_snapshot(symbol) or {}

            rows.append({
                "symbol": symbol,
                "composite_score": snapshot["composite_score"],
                "days_since_cross": snapshot["days_since_cross"],
                "spread_pct": snapshot["spread_pct"],
                "price_above_sma200_pct": snapshot["price_above_sma200_pct"],
                "volume_ratio": snapshot["volume_ratio"],
                "as_of": snapshot["as_of_date"],
                "weighted_quality_score": float(weighted_snapshot.get("quality_score", 0.0)),
                "consensus_label": _consensus_label(snapshot["composite_score"], weighted_snapshot.get("quality_score")),
                "math_url": _math_url("golden_cross_composite", symbol),
            })
        except Exception:
            continue

    rows.sort(key=lambda row: row["composite_score"], reverse=True)
    trimmed = rows[:5]
    for index, row in enumerate(trimmed, start=1):
        row["research_url"] = _research_url_with_source(
            row["symbol"],
            "Golden Cross Live Composite",
            index,
            float(row["composite_score"]),
            "golden_cross_composite",
        )

    response = {
        "valid": True,
        "as_of": _format_as_of(),
        "refresh_seconds": WATCHLIST_REFRESH_SECONDS,
        "results": trimmed,
    }
    cache.set(cache_key, response, WATCHLIST_REFRESH_SECONDS)
    return response


def get_golden_cross_weighted_watchlist() -> dict:
    cache_key = f"watchlist:golden_cross_weighted:v{GOLDEN_CROSS_WEIGHTED_CACHE_VERSION}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    rows: list[dict] = []
    for symbol in get_watchlist_universe():
        try:
            weighted_snapshot = get_weighted_golden_cross_snapshot(symbol)
            if not weighted_snapshot:
                continue
            live_snapshot = get_live_golden_cross_snapshot(symbol, require_active=False) or {}

            rows.append({
                "symbol": symbol,
                "quality_score": float(weighted_snapshot["quality_score"]),
                "win_rate": float(weighted_snapshot["win_rate"]),
                "avg_trade_return": float(weighted_snapshot["avg_trade_return"]),
                "total_return_pct": float(weighted_snapshot["total_return_pct"]),
                "max_drawdown": float(weighted_snapshot["max_drawdown"]),
                "trade_count": int(weighted_snapshot["trade_count"]),
                "live_composite_score": float(live_snapshot.get("composite_score", 0.0)),
                "consensus_label": _consensus_label(live_snapshot.get("composite_score"), weighted_snapshot["quality_score"]),
                "as_of": _format_as_of(),
                "math_url": _math_url("golden_cross_weighted", symbol),
            })
        except Exception:
            continue

    rows.sort(key=lambda row: row["quality_score"], reverse=True)
    trimmed = rows[:5]
    for index, row in enumerate(trimmed, start=1):
        row["research_url"] = _research_url_with_source(
            row["symbol"],
            "Golden Cross 10Y Weighted Backtest",
            index,
            float(row["quality_score"]),
            "golden_cross_weighted",
        )

    response = {
        "valid": True,
        "as_of": _format_as_of(),
        "refresh_seconds": WATCHLIST_REFRESH_SECONDS,
        "results": trimmed,
    }
    cache.set(cache_key, response, WATCHLIST_REFRESH_SECONDS)
    return response


def build_watchlist_signal_math_context(signal: str = "", ticker: str = "") -> dict:
    normalized_signal = (signal or "golden_cross_composite").strip().lower()
    if normalized_signal not in {"golden_cross_composite", "golden_cross_weighted"}:
        normalized_signal = "golden_cross_composite"

    live_leaderboard = get_golden_cross_watchlist()
    weighted_leaderboard = get_golden_cross_weighted_watchlist()
    candidate_symbol = (ticker or "").strip().upper()

    if not candidate_symbol:
        source_rows = weighted_leaderboard.get("results", []) if normalized_signal == "golden_cross_weighted" else live_leaderboard.get("results", [])
        if source_rows:
            candidate_symbol = source_rows[0]["symbol"]

    live_snapshot = get_live_golden_cross_snapshot(candidate_symbol, require_active=False) if candidate_symbol else None
    weighted_snapshot = get_weighted_golden_cross_snapshot(candidate_symbol) if candidate_symbol else None
    live_score = float((live_snapshot or {}).get("composite_score", 0.0))
    weighted_score = float((weighted_snapshot or {}).get("quality_score", 0.0))
    consensus_label = _consensus_label(live_score, weighted_score)

    composite_context = None
    if live_snapshot:
        composite_context = {
            "ticker": candidate_symbol,
            "formula": GOLDEN_CROSS_COMPOSITE_FORMULA,
            "score": live_score,
            "is_active": bool(live_snapshot.get("is_active")),
            "inputs": [
                {"label": "Bars since cross", "display": str(live_snapshot.get("bars_since_cross", 0))},
                {"label": "Days since cross", "display": str(live_snapshot.get("days_since_cross") or "—")},
                {"label": "50 / 200 spread", "display": f"{float(live_snapshot.get('spread_pct', 0.0)):.2f}%"},
                {"label": "Price above 50D", "display": f"{float(live_snapshot.get('price_above_sma50_pct', 0.0)):.2f}%"},
                {"label": "Price above 200D", "display": f"{float(live_snapshot.get('price_above_sma200_pct', 0.0)):.2f}%"},
                {"label": "Volume ratio", "display": f"{float(live_snapshot.get('volume_ratio', 0.0)):.2f}x"},
            ],
            "component_rows": [
                {"label": "Recency Score", "score": float(live_snapshot.get("component_scores", {}).get("recency_score", 0.0))},
                {"label": "Spread Score", "score": float(live_snapshot.get("component_scores", {}).get("spread_score", 0.0))},
                {"label": "Slope Score", "score": float(live_snapshot.get("component_scores", {}).get("slope_score", 0.0))},
                {"label": "Price Confirmation", "score": float(live_snapshot.get("component_scores", {}).get("price_confirmation", 0.0))},
                {"label": "Volume Confirmation", "score": float(live_snapshot.get("component_scores", {}).get("volume_confirmation", 0.0))},
            ],
            "math_url": _math_url("golden_cross_composite", candidate_symbol),
        }

    weighted_context = None
    if weighted_snapshot:
        weighted_context = {
            "ticker": candidate_symbol,
            "formula": GOLDEN_CROSS_WEIGHTED_FORMULA,
            "score": weighted_score,
            "metrics": [
                {"label": "Win rate", "display": f"{float(weighted_snapshot.get('win_rate', 0.0)) * 100:.2f}%"},
                {"label": "Avg trade return", "display": f"{float(weighted_snapshot.get('avg_trade_return', 0.0)) * 100:.2f}%"},
                {"label": "Total return", "display": f"{float(weighted_snapshot.get('total_return_pct', 0.0)) * 100:.2f}%"},
                {"label": "Max drawdown", "display": f"{float(weighted_snapshot.get('max_drawdown', 0.0)) * 100:.2f}%"},
                {"label": "Trade count", "display": str(int(weighted_snapshot.get('trade_count', 0)))},
            ],
            "component_rows": [
                {"label": "Win Rate Score", "score": float(weighted_snapshot.get("score_components", {}).get("win_rate_score", 0.0))},
                {"label": "Avg Trade Return Score", "score": float(weighted_snapshot.get("score_components", {}).get("avg_trade_return_score", 0.0))},
                {"label": "Total Return Score", "score": float(weighted_snapshot.get("score_components", {}).get("total_return_score", 0.0))},
                {"label": "Drawdown Score", "score": float(weighted_snapshot.get("score_components", {}).get("drawdown_score", 0.0))},
                {"label": "Trade Count Score", "score": float(weighted_snapshot.get("score_components", {}).get("trade_count_score", 0.0))},
            ],
            "window": weighted_snapshot.get("window", {}),
            "math_url": _math_url("golden_cross_weighted", candidate_symbol),
        }

    return {
        "selected_signal": normalized_signal,
        "selected_ticker": candidate_symbol,
        "composite": composite_context,
        "weighted": weighted_context,
        "comparison": {
            "consensus_label": consensus_label,
            "interpretation": _consensus_note(consensus_label),
            "live_score": live_score,
            "weighted_score": weighted_score,
        },
        "leaderboards": {
            "live": live_leaderboard,
            "weighted": weighted_leaderboard,
        },
    }
