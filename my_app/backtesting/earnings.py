from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Iterable

import pandas as pd
import yfinance as yf

MODE_NOTHING_SPECIAL = "nothing_special"
MODE_NEVER_TRADE = "never_trade"
MODE_ONLY_TRADE = "only_trade"
MODE_CUSTOM = "custom"

SUPPORTED_EARNINGS_MODES = {
    MODE_NOTHING_SPECIAL,
    MODE_NEVER_TRADE,
    MODE_ONLY_TRADE,
    MODE_CUSTOM,
}

DEFAULT_BLACKOUT_BEFORE_DAYS = 3
DEFAULT_BLACKOUT_AFTER_DAYS = 2

_MODE_ALIASES = {
    MODE_NOTHING_SPECIAL: MODE_NOTHING_SPECIAL,
    "nothing special": MODE_NOTHING_SPECIAL,
    "Nothing Special": MODE_NOTHING_SPECIAL,
    "none": MODE_NOTHING_SPECIAL,
    "off": MODE_NOTHING_SPECIAL,
    MODE_NEVER_TRADE: MODE_NEVER_TRADE,
    "never trade": MODE_NEVER_TRADE,
    "never trade earnings": MODE_NEVER_TRADE,
    "Never Trade Earnings": MODE_NEVER_TRADE,
    "never_trade_earnings": MODE_NEVER_TRADE,
    MODE_ONLY_TRADE: MODE_ONLY_TRADE,
    "only trade": MODE_ONLY_TRADE,
    "only trade earnings": MODE_ONLY_TRADE,
    "Only Trade Earnings": MODE_ONLY_TRADE,
    "only_trade_earnings": MODE_ONLY_TRADE,
    MODE_CUSTOM: MODE_CUSTOM,
    "custom earnings": MODE_CUSTOM,
    "Custom Earnings": MODE_CUSTOM,
    "custom_earnings": MODE_CUSTOM,
}


def _coerce_non_negative_int(value, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _normalize_mode(value) -> str:
    if value is None:
        return MODE_NOTHING_SPECIAL
    raw = str(value).strip()
    if not raw:
        return MODE_NOTHING_SPECIAL
    normalized = _MODE_ALIASES.get(raw)
    if normalized:
        return normalized
    underscored = raw.lower().replace(" ", "_")
    normalized = _MODE_ALIASES.get(underscored, underscored)
    return normalized if normalized in SUPPORTED_EARNINGS_MODES else MODE_NOTHING_SPECIAL


def _parse_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if value is None:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        try:
            parsed = pd.to_datetime(raw, errors="coerce")
        except Exception:
            return None
        if pd.isna(parsed):
            return None
        return parsed.date()


def _normalize_dates(values: Iterable | None) -> list[str]:
    unique_dates: set[date] = set()
    for item in values or []:
        parsed = _parse_date(item)
        if parsed is not None:
            unique_dates.add(parsed)
    return [item.isoformat() for item in sorted(unique_dates)]


def normalize_earnings_config(raw_config: dict | None) -> dict:
    if isinstance(raw_config, dict):
        source = raw_config
    else:
        source = {"mode": raw_config}

    mode = _normalize_mode(source.get("mode"))
    custom_mode = _normalize_mode(source.get("custom_mode"))
    if custom_mode not in {MODE_NEVER_TRADE, MODE_ONLY_TRADE}:
        custom_mode = MODE_NEVER_TRADE

    blackout_before_days = _coerce_non_negative_int(
        source.get("blackout_before_days", source.get("before_days")),
        DEFAULT_BLACKOUT_BEFORE_DAYS,
    )
    blackout_after_days = _coerce_non_negative_int(
        source.get("blackout_after_days", source.get("after_days")),
        DEFAULT_BLACKOUT_AFTER_DAYS,
    )
    earnings_dates = _normalize_dates(source.get("earnings_dates") or source.get("dates") or [])

    return {
        "mode": mode,
        "earnings_dates": earnings_dates,
        "blackout_before_days": blackout_before_days,
        "blackout_after_days": blackout_after_days,
        "custom_mode": custom_mode,
    }


def _coerce_to_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        parsed = _parse_date(value)
        if parsed is not None:
            return parsed
    raise ValueError("Expected date-compatible value.")


@lru_cache(maxsize=256)
def _fetch_earnings_dates_cached(ticker: str, start_date_iso: str, end_date_iso: str) -> tuple[str, ...]:
    try:
        earnings_table = yf.Ticker(ticker).get_earnings_dates(limit=80)
    except Exception:
        return ()

    if earnings_table is None or earnings_table.empty:
        return ()

    try:
        start_date = _coerce_to_date(start_date_iso) - timedelta(days=14)
        end_date = _coerce_to_date(end_date_iso) + timedelta(days=14)
    except ValueError:
        return ()

    if isinstance(earnings_table.index, pd.DatetimeIndex):
        earnings_index = pd.to_datetime(earnings_table.index, utc=True, errors="coerce")
    elif "Earnings Date" in earnings_table.columns:
        earnings_index = pd.to_datetime(earnings_table["Earnings Date"], utc=True, errors="coerce")
    else:
        earnings_index = pd.to_datetime(earnings_table.index, utc=True, errors="coerce")

    dates: set[date] = set()
    for timestamp in earnings_index:
        if pd.isna(timestamp):
            continue
        event_date = timestamp.date()
        if start_date <= event_date <= end_date:
            dates.add(event_date)

    return tuple(item.isoformat() for item in sorted(dates))


def fetch_earnings_dates(
    ticker: str,
    start_date: date | str,
    end_date: date | str,
) -> list[str]:
    normalized_ticker = (ticker or "").upper().strip()
    if not normalized_ticker:
        return []

    try:
        start_date_iso = _coerce_to_date(start_date).isoformat()
        end_date_iso = _coerce_to_date(end_date).isoformat()
    except ValueError:
        return []

    return list(_fetch_earnings_dates_cached(normalized_ticker, start_date_iso, end_date_iso))


def resolve_earnings_config(
    raw_config: dict | None,
    ticker: str,
    start_date: date | str,
    end_date: date | str,
) -> dict:
    config = normalize_earnings_config(raw_config)
    if config["mode"] == MODE_NOTHING_SPECIAL or config["earnings_dates"]:
        return config

    resolved_dates = fetch_earnings_dates(ticker, start_date, end_date)
    if resolved_dates:
        config["earnings_dates"] = resolved_dates
    return config


def build_earnings_blackout_dates(config: dict | None) -> set[date]:
    normalized = normalize_earnings_config(config)
    blackout_before_days = int(normalized["blackout_before_days"])
    blackout_after_days = int(normalized["blackout_after_days"])
    blackout_dates: set[date] = set()

    for event_date_raw in normalized["earnings_dates"]:
        event_date = _parse_date(event_date_raw)
        if event_date is None:
            continue
        for offset in range(-blackout_before_days, blackout_after_days + 1):
            blackout_dates.add(event_date + timedelta(days=offset))

    return blackout_dates


def _extract_trade_dates(df: pd.DataFrame) -> pd.Series:
    if "Date_dt" in df.columns:
        raw = pd.to_datetime(df["Date_dt"], errors="coerce")
    elif "Date" in df.columns:
        raw = pd.to_datetime(df["Date"], unit="s", errors="coerce")
    else:
        return pd.Series([None] * len(df), index=df.index, dtype="object")

    return pd.Series(
        [value.date() if pd.notna(value) else None for value in raw],
        index=df.index,
        dtype="object",
    )


def build_entry_permission_mask(df: pd.DataFrame, config: dict | None) -> pd.Series:
    normalized = normalize_earnings_config(config)
    mode = normalized["mode"]

    if mode == MODE_NOTHING_SPECIAL:
        return pd.Series(True, index=df.index, dtype=bool)

    effective_mode = mode
    if mode == MODE_CUSTOM:
        effective_mode = normalized.get("custom_mode") or MODE_NEVER_TRADE
        if effective_mode not in {MODE_NEVER_TRADE, MODE_ONLY_TRADE}:
            effective_mode = MODE_NEVER_TRADE

    blackout_dates = build_earnings_blackout_dates(normalized)
    if not blackout_dates:
        default_permission = False if effective_mode == MODE_ONLY_TRADE else True
        return pd.Series(default_permission, index=df.index, dtype=bool)

    trade_dates = _extract_trade_dates(df)
    in_blackout = trade_dates.map(lambda item: item in blackout_dates if item is not None else False)
    if effective_mode == MODE_ONLY_TRADE:
        return in_blackout.astype(bool)
    return (~in_blackout).astype(bool)
