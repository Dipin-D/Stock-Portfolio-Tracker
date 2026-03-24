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
    today = timezone.localdate().isoformat()
    params = {
        "ticker": symbol.upper(),
        "start_date": "1993-01-01",
        "end_date": today,
        "autoload": "1",
        "analysis_mode": "single",
        "prior_mode": "universe",
        "prefill_strategy": "golden_cross",
    }
    if source_context:
        for key in ("source_list", "source_rank", "source_score", "source_signal"):
            value = source_context.get(key)
            if value not in (None, ""):
                params[key] = value
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

    signal_breakdown = _non_empty_items([
        {"label": "Composite Score", "display": f"{golden_cross['composite_score']:.2f} / 100"},
        {"label": "50/200 Spread", "display": _format_percent((golden_cross.get("spread_pct") or 0) / 100.0)},
        {"label": "Price vs 200D", "display": _format_percent((golden_cross.get("price_above_sma200_pct") or 0) / 100.0)},
        {"label": "Volume Ratio", "display": _format_number(golden_cross.get("volume_ratio"), 2)},
        {"label": "Days Since Cross", "display": _format_int(golden_cross.get("days_since_cross"))},
        {"label": "Last Cross Date", "display": golden_cross.get("last_cross_date")},
    ])

    signal_component_cards = _non_empty_items([
        {"label": "Recency", "display": _format_percent(golden_cross.get("component_scores", {}).get("recency_score"))},
        {"label": "Spread", "display": _format_percent(golden_cross.get("component_scores", {}).get("spread_score"))},
        {"label": "Slope", "display": _format_percent(golden_cross.get("component_scores", {}).get("slope_score"))},
        {"label": "Price Confirmation", "display": _format_percent(golden_cross.get("component_scores", {}).get("price_confirmation"))},
        {"label": "Volume Confirmation", "display": _format_percent(golden_cross.get("component_scores", {}).get("volume_confirmation"))},
    ])

    return {
        "ticker": normalized_symbol,
        "company_name": info.get("longName") or info.get("shortName") or normalized_symbol,
        "company_summary": info.get("longBusinessSummary") or "",
        "market_snapshot_items": market_snapshot_items,
        "fundamentals_items": fundamentals_items,
        "growth_items": growth_items,
        "golden_cross": {
            "state_label": "Active" if golden_cross["is_active"] else "Inactive",
            "state_class": "is-active" if golden_cross["is_active"] else "is-inactive",
            "composite_score": golden_cross["composite_score"],
            "signal_breakdown": signal_breakdown,
            "component_cards": signal_component_cards,
            "as_of": golden_cross["as_of_date"],
            "fast_sma": _format_currency(golden_cross.get("sma_50")),
            "slow_sma": _format_currency(golden_cross.get("sma_200")),
            "price": _format_currency(golden_cross.get("latest_close")),
        },
        "backtest_url": build_research_backtest_url(normalized_symbol, source_context=source_context),
    }
