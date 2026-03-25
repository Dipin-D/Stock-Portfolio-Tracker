from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlencode

import pandas as pd
import yfinance as yf
from django.core.cache import cache
from django.utils import timezone

from my_app.services.watchlist_service import compute_golden_cross_snapshot
from my_app.utils import PriceDataError, download_n_clean_data


RESEARCH_INFO_CACHE_SECONDS = 1800
RESEARCH_PRICE_CACHE_SECONDS = 1800
SOURCE_SIGNAL_LABELS = {
    "golden_cross_composite": "Golden Cross Live Composite",
    "golden_cross_weighted": "Golden Cross 10Y Weighted Backtest",
    "momentum_60": "Momentum 60-Day Leaders",
    "momentum_120": "Momentum 120-Day Leaders",
    "momentum_12m": "Momentum 12M",
}
MOMENTUM_SOURCE_SIGNALS = {"momentum_60", "momentum_120", "momentum_12m"}
MOMENTUM_SCORE_LABELS = {
    "momentum_60": "60-Day Momentum Score",
    "momentum_120": "120-Day Momentum Score",
    "momentum_12m": "12-Month Momentum Score",
}


def _format_percent(value: float | None, digits: int = 2) -> str | None:
    if value is None or pd.isna(value):
        return None
    return f"{float(value) * 100:.{digits}f}%"


def _format_currency(value: float | int | None, digits: int = 2) -> str | None:
    if value is None or pd.isna(value):
        return None
    return f"${float(value):,.{digits}f}"


def _format_number(value: float | int | None, digits: int = 2) -> str | None:
    if value is None or pd.isna(value):
        return None
    return f"{float(value):,.{digits}f}"


def _format_int(value: float | int | None) -> str | None:
    if value is None or pd.isna(value):
        return None
    return f"{int(round(float(value))):,}"


def _compact_currency(value: float | int | None) -> str | None:
    if value is None or pd.isna(value):
        return None

    numeric = float(value)
    thresholds = [
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
    ]
    for threshold, suffix in thresholds:
        if abs(numeric) >= threshold:
            return f"${numeric / threshold:,.2f}{suffix}"
    return _format_currency(numeric)


def _parse_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_source_context(source_context: dict | None) -> dict:
    if not source_context:
        return {}

    normalized = {}
    for key in ("source_list", "source_rank", "source_score", "source_signal"):
        raw_value = source_context.get(key)
        if raw_value in (None, ""):
            continue
        normalized[key] = str(raw_value).strip()

    return {key: value for key, value in normalized.items() if value}


def _is_momentum_source_signal(source_signal: str) -> bool:
    return str(source_signal or "").strip().lower() in MOMENTUM_SOURCE_SIGNALS


def _cached_info(symbol: str) -> dict:
    cache_key = f"research:info:{symbol.upper()}:v1"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    ticker = yf.Ticker(symbol)
    try:
        info = dict(ticker.info or {})
    except Exception:
        info = {}
    cache.set(cache_key, info, RESEARCH_INFO_CACHE_SECONDS)
    return info


def _cached_price_frame(symbol: str) -> pd.DataFrame:
    cache_key = f"research:price:{symbol.upper()}:v1"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    today = timezone.localdate()
    start_date = (today - timedelta(days=900)).isoformat()
    frame = download_n_clean_data(symbol, start_date, today.isoformat(), compute_sma=True)
    cache.set(cache_key, frame, RESEARCH_PRICE_CACHE_SECONDS)
    return frame


def _normalize_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized["Date_dt"] = pd.to_datetime(normalized["Date"], unit="s", errors="coerce")
    normalized = normalized.dropna(subset=["Date_dt"]).sort_values("Date_dt").reset_index(drop=True)
    return normalized


def _latest_return(frame: pd.DataFrame, bars_back: int) -> float | None:
    if len(frame) <= bars_back:
        return None
    latest_close = float(frame.iloc[-1]["Close"])
    past_close = float(frame.iloc[-1 - bars_back]["Close"])
    if latest_close <= 0 or past_close <= 0:
        return None
    return (latest_close / past_close) - 1.0


def build_research_backtest_url(symbol: str, source_context: dict | None = None) -> str:
    cleaned_source_context = _clean_source_context(source_context)
    source_signal = cleaned_source_context.get("source_signal", "").lower()
    prefill_strategy = "momentum_12m" if _is_momentum_source_signal(source_signal) else "golden_cross"
    today = timezone.localdate().isoformat()
    params = {
        "ticker": symbol.upper(),
        "start_date": "1993-01-01",
        "end_date": today,
        "autoload": "1",
        "analysis_mode": "single",
        "prior_mode": "universe",
        "prefill_strategy": prefill_strategy,
    }
    params.update(cleaned_source_context)
    query = urlencode(params)
    return f"/backtest/?{query}"


def _non_empty_items(items: list[dict]) -> list[dict]:
    return [item for item in items if item.get("display")]


def build_research_payload(symbol: str, source_context: dict | None = None) -> dict:
    normalized_symbol = symbol.upper().strip()
    if not normalized_symbol:
        raise PriceDataError("Ticker is required.")

    price_frame = _cached_price_frame(normalized_symbol)
    if price_frame.empty:
        raise PriceDataError(f"No research data returned for {normalized_symbol}.")

    normalized_frame = _normalize_price_frame(price_frame)
    latest = normalized_frame.iloc[-1]
    previous = normalized_frame.iloc[-2] if len(normalized_frame) > 1 else latest
    info = _cached_info(normalized_symbol)
    golden_cross = compute_golden_cross_snapshot(normalized_frame, require_active=False) or {
        "is_active": False,
        "composite_score": 0.0,
        "days_since_cross": None,
        "last_cross_date": None,
        "spread_pct": None,
        "price_above_sma200_pct": None,
        "price_above_sma50_pct": None,
        "volume_ratio": None,
        "latest_close": round(float(latest["Close"]), 2),
        "sma_50": None,
        "sma_200": None,
        "component_scores": {},
        "as_of_date": latest["Date_dt"].date().isoformat(),
    }

    last_close = float(latest["Close"])
    previous_close = float(previous["Close"]) if previous is not None else last_close
    daily_change = (last_close / previous_close - 1.0) if previous_close else None
    trailing_year = normalized_frame.loc[normalized_frame["Date_dt"] >= (normalized_frame.iloc[-1]["Date_dt"] - pd.Timedelta(days=365))]

    market_snapshot_items = _non_empty_items([
        {"label": "Last Price", "display": _format_currency(last_close)},
        {"label": "Daily Move", "display": _format_percent(daily_change)},
        {"label": "1 Month Return", "display": _format_percent(_latest_return(normalized_frame, 21))},
        {"label": "6 Month Return", "display": _format_percent(_latest_return(normalized_frame, 126))},
        {"label": "1 Year Return", "display": _format_percent(_latest_return(normalized_frame, 252))},
        {
            "label": "52-Week Range",
            "display": (
                f"{_format_currency(trailing_year['Low'].min())} - {_format_currency(trailing_year['High'].max())}"
                if not trailing_year.empty else None
            ),
        },
        {"label": "Average Volume", "display": _format_int(info.get("averageVolume") or info.get("averageDailyVolume10Day"))},
        {"label": "Beta", "display": _format_number(info.get("beta"), 2)},
        {"label": "Market Cap", "display": _compact_currency(info.get("marketCap"))},
    ])

    fundamentals_items = _non_empty_items([
        {"label": "Trailing P/E", "display": _format_number(info.get("trailingPE"), 2)},
        {"label": "Forward P/E", "display": _format_number(info.get("forwardPE"), 2)},
        {"label": "PEG Ratio", "display": _format_number(info.get("pegRatio"), 2)},
        {"label": "Price / Book", "display": _format_number(info.get("priceToBook"), 2)},
        {"label": "EV / Revenue", "display": _format_number(info.get("enterpriseToRevenue"), 2)},
        {"label": "EV / EBITDA", "display": _format_number(info.get("enterpriseToEbitda"), 2)},
        {"label": "Dividend Yield", "display": _format_percent(info.get("dividendYield"))},
        {"label": "Sector", "display": info.get("sector")},
        {"label": "Industry", "display": info.get("industry")},
    ])

    growth_items = _non_empty_items([
        {"label": "Revenue Growth", "display": _format_percent(info.get("revenueGrowth"))},
        {"label": "Earnings Growth", "display": _format_percent(info.get("earningsGrowth"))},
        {"label": "Gross Margin", "display": _format_percent(info.get("grossMargins"))},
        {"label": "Operating Margin", "display": _format_percent(info.get("operatingMargins"))},
        {"label": "Net Margin", "display": _format_percent(info.get("profitMargins"))},
        {"label": "Return on Equity", "display": _format_percent(info.get("returnOnEquity"))},
        {"label": "Return on Assets", "display": _format_percent(info.get("returnOnAssets"))},
        {"label": "EPS", "display": _format_number(info.get("trailingEps"), 2)},
    ])

    cleaned_source_context = _clean_source_context(source_context)
    source_signal = cleaned_source_context.get("source_signal", "").lower()
    source_signal_label = SOURCE_SIGNAL_LABELS.get(source_signal, cleaned_source_context.get("source_signal", ""))
    source_rank = _parse_int(cleaned_source_context.get("source_rank"))
    source_score = _parse_float(cleaned_source_context.get("source_score"))
    is_momentum_source = _is_momentum_source_signal(source_signal)

    momentum_returns = {
        "momentum_60": _latest_return(normalized_frame, 60),
        "momentum_120": _latest_return(normalized_frame, 120),
        "momentum_12m": _latest_return(normalized_frame, 252),
    }
    active_momentum_signal = source_signal if source_signal in MOMENTUM_SOURCE_SIGNALS else "momentum_60"
    active_momentum_value = momentum_returns.get(active_momentum_signal)
    momentum_state_positive = active_momentum_value is not None and active_momentum_value > 0
    momentum_state_label = "Positive" if momentum_state_positive else "Negative / Flat"
    momentum_state_class = "is-active" if momentum_state_positive else "is-inactive"
    momentum_score_display = (
        f"{source_score:.2f}%"
        if source_score is not None
        else (_format_percent(active_momentum_value) or "Unavailable")
    )

    golden_cross_signal_breakdown = _non_empty_items([
        {"label": "Composite Score", "display": f"{golden_cross['composite_score']:.2f} / 100"},
        {"label": "50/200 Spread", "display": _format_percent((golden_cross.get("spread_pct") or 0) / 100.0)},
        {"label": "Price vs 200D", "display": _format_percent((golden_cross.get("price_above_sma200_pct") or 0) / 100.0)},
        {"label": "Volume Ratio", "display": _format_number(golden_cross.get("volume_ratio"), 2)},
        {"label": "Days Since Cross", "display": _format_int(golden_cross.get("days_since_cross"))},
        {"label": "Last Cross Date", "display": golden_cross.get("last_cross_date")},
    ])

    golden_cross_component_cards = _non_empty_items([
        {"label": "Fast SMA", "display": _format_currency(golden_cross.get("sma_50"))},
        {"label": "Slow SMA", "display": _format_currency(golden_cross.get("sma_200"))},
        {"label": "Last Price", "display": _format_currency(golden_cross.get("latest_close"))},
        {"label": "Recency", "display": _format_percent(golden_cross.get("component_scores", {}).get("recency_score"))},
        {"label": "Spread", "display": _format_percent(golden_cross.get("component_scores", {}).get("spread_score"))},
        {"label": "Slope", "display": _format_percent(golden_cross.get("component_scores", {}).get("slope_score"))},
        {"label": "Price Confirmation", "display": _format_percent(golden_cross.get("component_scores", {}).get("price_confirmation"))},
        {"label": "Volume Confirmation", "display": _format_percent(golden_cross.get("component_scores", {}).get("volume_confirmation"))},
    ])

    signal_section_kicker = "Golden Cross Signal"
    signal_section_title = "Trend confirmation"
    signal_section_subcopy = "This is the same crossover score driving the watchlist ranking, broken into its working parts."
    signal_state_heading = "Signal State"
    signal_state_label = "Active" if golden_cross["is_active"] else "Inactive"
    signal_state_class = "is-active" if golden_cross["is_active"] else "is-inactive"
    signal_breakdown_items = golden_cross_signal_breakdown
    signal_component_cards = golden_cross_component_cards
    hero_primary_label = "Golden Cross Score"
    hero_primary_value = f"{golden_cross['composite_score']:.2f}"
    backtest_handoff_label = "Single + Universe + GC"
    backtest_cta_copy = (
        f"Move into the existing Backtest shell with {normalized_symbol} preloaded, the chart ready to render, "
        "and Golden Cross prepared as the first strategy step."
    )

    if is_momentum_source:
        signal_section_kicker = "Momentum Signal"
        signal_section_title = "Relative strength context"
        signal_section_subcopy = (
            "This ticker arrived through the momentum leaderboard. Use this return profile first, then compare it "
            "against trend confirmation before running Backtest."
        )
        signal_state_heading = "Momentum State"
        signal_state_label = momentum_state_label
        signal_state_class = momentum_state_class
        signal_breakdown_items = _non_empty_items([
            {
                "label": MOMENTUM_SCORE_LABELS.get(active_momentum_signal, "Momentum Score"),
                "display": momentum_score_display,
            },
            {"label": "60-Day Momentum", "display": _format_percent(momentum_returns["momentum_60"])},
            {"label": "120-Day Momentum", "display": _format_percent(momentum_returns["momentum_120"])},
            {"label": "12-Month Momentum", "display": _format_percent(momentum_returns["momentum_12m"])},
            {"label": "Leaderboard Rank", "display": f"#{source_rank}" if source_rank else None},
            {"label": "As Of", "display": golden_cross.get("as_of_date")},
        ])
        signal_component_cards = _non_empty_items([
            {"label": "Daily Move", "display": _format_percent(daily_change)},
            {"label": "1 Month Return", "display": _format_percent(_latest_return(normalized_frame, 21))},
            {"label": "6 Month Return", "display": _format_percent(_latest_return(normalized_frame, 126))},
            {"label": "1 Year Return", "display": _format_percent(_latest_return(normalized_frame, 252))},
            {"label": "Last Price", "display": _format_currency(last_close)},
            {"label": "Average Volume", "display": _format_int(info.get("averageVolume") or info.get("averageDailyVolume10Day"))},
        ])
        hero_primary_label = MOMENTUM_SCORE_LABELS.get(active_momentum_signal, "Momentum Score")
        hero_primary_value = momentum_score_display
        backtest_handoff_label = "Single + Universe + Momentum"
        backtest_cta_copy = (
            f"Move into the existing Backtest shell with {normalized_symbol} preloaded, the chart ready to render, "
            "and Momentum prepared as the first strategy step."
        )

    golden_cross_state_label = "Active" if golden_cross["is_active"] else "Inactive"
    golden_cross_state_class = "is-active" if golden_cross["is_active"] else "is-inactive"

    return {
        "ticker": normalized_symbol,
        "company_name": info.get("longName") or info.get("shortName") or normalized_symbol,
        "company_summary": info.get("longBusinessSummary") or "",
        "market_snapshot_items": market_snapshot_items,
        "fundamentals_items": fundamentals_items,
        "growth_items": growth_items,
        "source_context": cleaned_source_context or None,
        "source_signal_label": source_signal_label,
        "is_momentum_source": is_momentum_source,
        "hero_primary_label": hero_primary_label,
        "hero_primary_value": hero_primary_value,
        "signal_state_heading": signal_state_heading,
        "signal_state_label": signal_state_label,
        "signal_state_class": signal_state_class,
        "signal_section_kicker": signal_section_kicker,
        "signal_section_title": signal_section_title,
        "signal_section_subcopy": signal_section_subcopy,
        "signal_breakdown_items": signal_breakdown_items,
        "signal_component_cards": signal_component_cards,
        "backtest_handoff_label": backtest_handoff_label,
        "backtest_cta_copy": backtest_cta_copy,
        "golden_cross": {
            "state_label": golden_cross_state_label,
            "state_class": golden_cross_state_class,
            "composite_score": golden_cross["composite_score"],
            "signal_breakdown": golden_cross_signal_breakdown,
            "component_cards": golden_cross_component_cards,
            "as_of": golden_cross["as_of_date"],
            "fast_sma": _format_currency(golden_cross.get("sma_50")),
            "slow_sma": _format_currency(golden_cross.get("sma_200")),
            "price": _format_currency(golden_cross.get("latest_close")),
        },
        "backtest_url": build_research_backtest_url(normalized_symbol, source_context=cleaned_source_context),
    }
