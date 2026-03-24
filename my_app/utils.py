# ── utils.py ────────────────────────────────────────────────────────────────
import hashlib, logging, random, time, json
from io import StringIO
from typing import Final, Optional, Tuple
from urllib import error as urllib_error, parse as urllib_parse, request as urllib_request

import numpy as np
import pandas as pd
import yfinance as yf
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

# yfinance 0.2.37+: YFRateLimitError lives here; fall back to a generic error
try:
    from yfinance.exceptions import YFRateLimitError
except ImportError:         # fallback if yfinance version is old or path changed
    class YFRateLimitError(Exception):  # type: ignore
        pass

log = logging.getLogger(__name__)


class PriceDataError(Exception):
    """Application-level error for unavailable or invalid market data."""


def _format_download_error(symbol: str, error: Exception) -> str:
    if isinstance(error, PriceDataError):
        return str(error)

    if isinstance(error, YFRateLimitError):
        return "Yahoo Finance rate limited the request. Please try again in a moment."

    if isinstance(error, urllib_error.HTTPError):
        if error.code in {401, 403}:
            return "Yahoo Finance rejected the request. Please try again in a moment."
        if error.code == 404:
            return f"No price data returned for {symbol}."
        return f"Yahoo Finance returned HTTP {error.code} while loading {symbol}."

    if isinstance(error, urllib_error.URLError):
        reason = getattr(error, 'reason', error)
        if isinstance(reason, TimeoutError):
            return "Timed out while contacting Yahoo Finance."
        return "Unable to reach Yahoo Finance right now. Check your internet or DNS connection and try again."

    if isinstance(error, TimeoutError):
        return "Timed out while contacting Yahoo Finance."

    if isinstance(error, ValueError):
        message = str(error).strip()
        if message:
            return message

    return f"Unable to download price data for {symbol} right now."


def _raise_price_data_error(symbol: str, error: Exception):
    raise PriceDataError(_format_download_error(symbol, error)) from error

# Keep a long/lazy cache timeout; we control staleness with our own timestamp
CACHE_SCHEMA_VERSION: Final[int] = 2
CACHE_TIMEOUT: Final[Optional[int]] = None   # don't auto-expire; we expire by policy
FRESHNESS_DAYS: Final[int] = 10              # ← your “auto-refresh every 10 days”
LOCK_TTL_SEC: Final[int] = 60                # small lock to prevent stampede

# --------------------------------------------------------------------------- #
# Keys
# --------------------------------------------------------------------------- #
def _make_cache_key(symbol: str, start: str, end: str, sma: bool) -> str:
    raw = f"v{CACHE_SCHEMA_VERSION}|{symbol}|{start}|{end}|{int(sma)}"
    return "stockdata:" + hashlib.sha1(raw.encode()).hexdigest()

def _make_lock_key(cache_key: str) -> str:
    return f"{cache_key}:lock"

# --------------------------------------------------------------------------- #
# Time helpers
# --------------------------------------------------------------------------- #
def _now():
    # Use timezone-aware now if Django is TZ-aware
    try:
        return timezone.now()
    except Exception:
        # Fallback – but Django projects usually have timezone available
        return pd.Timestamp.utcnow()

def _is_fresh(ts_iso: Optional[str]) -> bool:
    if not ts_iso:
        return False
    try:
        ts = pd.Timestamp(ts_iso)
    except Exception:
        return False
    return (_now() - ts) < timedelta(days=FRESHNESS_DAYS)

# --------------------------------------------------------------------------- #
# Cache helpers (store payload + timestamp)
# --------------------------------------------------------------------------- #
def _cache_get(cache_key: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (json_payload, ts_iso) if present, else (None, None).
    """
    blob = cache.get(cache_key)
    if not blob:
        return None, None
    # Support both old (raw JSON string) and new (dict with ts/payload) formats
    if isinstance(blob, dict) and "payload" in blob and "ts" in blob:
        return blob["payload"], blob["ts"]
    if isinstance(blob, str):
        # legacy path: no timestamp -> treat as stale but usable
        return blob, None
    return None, None

def _cache_set(cache_key: str, json_payload: str):
    cache.set(cache_key, {"payload": json_payload, "ts": _now().isoformat()}, CACHE_TIMEOUT)


def _load_cached_frame(cached_json: str, compute_sma: bool) -> pd.DataFrame:
    cached_df = pd.read_json(StringIO(cached_json), orient="split")
    return _normalize_download_frame(cached_df, compute_sma)


def _normalize_download_frame(df: pd.DataFrame, compute_sma: bool) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("No price data returned from provider.")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.copy()
    if "Date" not in df.columns:
        df = df.reset_index()

    required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    if not set(required_columns).issubset(df.columns):
        raise ValueError(f"Price dataset missing required columns: {required_columns}")

    df = df[required_columns]
    if pd.api.types.is_numeric_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date'], unit='s', errors='coerce')
    else:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date')
    df['Date'] = df['Date'].apply(lambda x: x.timestamp())

    if compute_sma:
        df['sma_50'] = df['Close'].rolling(50).mean()
        df['sma_200'] = df['Close'].rolling(200).mean()

    df.replace({np.nan: None}, inplace=True)
    return df


def serialize_price_frame(df: pd.DataFrame, compute_sma: bool = True) -> list[dict]:
    normalized_df = _normalize_download_frame(df, compute_sma)
    json_safe_df = normalized_df.astype(object).where(pd.notna(normalized_df), None)
    return json_safe_df.to_dict(orient='records')


def _download_via_ticker_history(symbol: str, start: str, end: str) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    return ticker.history(
        start=start,
        end=end,
        auto_adjust=True,
        actions=False,
        repair=True,
    )


def _download_from_yahoo_chart(symbol: str, start: str, end: str) -> pd.DataFrame:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) + pd.Timedelta(days=1)

    if start_ts.tzinfo is None:
        start_ts = start_ts.tz_localize('UTC')
    if end_ts.tzinfo is None:
        end_ts = end_ts.tz_localize('UTC')

    params = urllib_parse.urlencode({
        'period1': int(start_ts.timestamp()),
        'period2': int(end_ts.timestamp()),
        'interval': '1d',
        'includeAdjustedClose': 'true',
        'events': 'history',
    })
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib_parse.quote(symbol)}?{params}"
    req = urllib_request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
    })

    with urllib_request.urlopen(req, timeout=15) as response:
        payload = json.loads(response.read().decode('utf-8'))

    chart = (payload or {}).get('chart', {})
    if chart.get('error'):
        raise ValueError(chart['error'].get('description') or 'Yahoo chart API returned an error.')

    result = (chart.get('result') or [None])[0]
    if not result:
        raise ValueError('Yahoo chart API returned no result.')

    timestamps = result.get('timestamp') or []
    quote = ((result.get('indicators') or {}).get('quote') or [{}])[0]
    if not timestamps or not quote:
        raise ValueError('Yahoo chart API returned no rows.')

    frame = pd.DataFrame({
        'Date': pd.to_datetime(timestamps, unit='s', utc=True).tz_localize(None),
        'Open': quote.get('open', []),
        'High': quote.get('high', []),
        'Low': quote.get('low', []),
        'Close': quote.get('close', []),
        'Volume': quote.get('volume', []),
    })

    frame = frame.dropna(subset=['Open', 'High', 'Low', 'Close'])
    if frame.empty:
        raise ValueError('Yahoo chart API returned only empty candles.')

    return frame.set_index('Date')

# --------------------------------------------------------------------------- #
# Downloader with retry / back-off
# --------------------------------------------------------------------------- #
def _download_with_retry(symbol: str, start: str, end: str,
                         max_tries: int = 5) -> pd.DataFrame:
    """
    Call yf.download with exponential back-off.
    Raises the last exception if all retries fail.
    """
    last_error = None

    for attempt in range(max_tries):
        try:
            frame = yf.download(
                symbol,
                start=start,
                end=end,
                auto_adjust=True,
                progress=False,
                threads=False,
                group_by='column',
            )
            if frame is not None and not frame.empty:
                return frame
            last_error = ValueError("yfinance download returned no rows.")
        except YFRateLimitError as error:
            last_error = error
            wait = 2 ** attempt + random.random()
            log.warning("Rate-limited on %s (try %s/%s) – sleeping %.1fs",
                        symbol, attempt + 1, max_tries, wait)
            time.sleep(wait)
            continue
        except Exception as error:
            last_error = error

        try:
            frame = _download_via_ticker_history(symbol, start, end)
            if frame is not None and not frame.empty:
                return frame
            last_error = ValueError("yfinance ticker history returned no rows.")
        except Exception as error:
            last_error = error

        try:
            frame = _download_from_yahoo_chart(symbol, start, end)
            if frame is not None and not frame.empty:
                return frame
            last_error = ValueError("Yahoo chart endpoint returned no rows.")
        except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, ValueError) as error:
            last_error = error

        wait = min(2 ** attempt + random.random(), 8)
        time.sleep(wait)

    if last_error:
        raise last_error
    raise ValueError(f"Exceeded {max_tries} download attempts for {symbol}")

# --------------------------------------------------------------------------- #
# Public helpers
# --------------------------------------------------------------------------- #
def download_n_clean_data(symbol: str,
                          start_date: str,
                          end_date: str,
                          compute_sma: bool = True) -> pd.DataFrame:
    """
    Download (with caching + 10-day freshness policy) + normalize columns
    + add optional SMA columns. Returns a pandas DataFrame with:
      ['Date'(epoch seconds), 'Open','High','Low','Close','Volume', (opt) 'sma_50','sma_200']
    """
    cache_key = _make_cache_key(symbol, start_date, end_date, compute_sma)

    # ---------- 1) check cache ---------- #
    cached_json, cached_ts = _cache_get(cache_key)
    if cached_json and _is_fresh(cached_ts):
        # Fresh: fast path
        # print("Serving fresh cached data")  # optional: keep quiet in prod
        return _load_cached_frame(cached_json, compute_sma)

    # ---------- 2) try to refresh (lock to avoid stampede) ---------- #
    lock_key = _make_lock_key(cache_key)
    got_lock = cache.add(lock_key, True, timeout=LOCK_TTL_SEC)

    if got_lock:
        try:
            # Download from Yahoo
            df = _download_with_retry(symbol, start_date, end_date)
            df = _normalize_download_frame(df, compute_sma)

            # Store as JSON + timestamp
            json_payload = df.to_json(orient="split")
            _cache_set(cache_key, json_payload)

            # print("Downloaded data from Yahoo")  # optional
            return df

        except Exception as error:
            # If the live source fails and we have *any* cached payload (even stale), serve it.
            if cached_json:
                log.warning("Serving *stale* cached data for %s because live refresh failed", symbol)
                return _load_cached_frame(cached_json, compute_sma)
            _raise_price_data_error(symbol, error)

        finally:
            cache.delete(lock_key)

    else:
        # Another worker is refreshing; short backoff then use whatever is in cache
        time.sleep(1.0)
        cached_json2, _ = _cache_get(cache_key)
        if cached_json2:
            return _load_cached_frame(cached_json2, compute_sma)
        # If still empty (first ever call and lock holder failed fast), make a direct attempt
        try:
            df = _download_with_retry(symbol, start_date, end_date)
        except Exception as error:
            _raise_price_data_error(symbol, error)
        df = _normalize_download_frame(df, compute_sma)
        _cache_set(cache_key, df.to_json(orient="split"))
        return df

def get_cached_last_update(symbol: str, start_date: str, end_date: str, compute_sma: bool = True) -> Optional[pd.Timestamp]:
    """
    Returns the pandas.Timestamp of the cached dataset, or None if not cached.
    """
    cache_key = _make_cache_key(symbol, start_date, end_date, compute_sma)
    _, ts_iso = _cache_get(cache_key)
    return pd.Timestamp(ts_iso) if ts_iso else None

def invalidate_cache(symbol: str, start_date: str, end_date: str, compute_sma: bool = True) -> None:
    """
    Force the next call to refresh by deleting the cache entry.
    """
    cache_key = _make_cache_key(symbol, start_date, end_date, compute_sma)
    cache.delete(cache_key)

# Existing momentum helper kept as-is (compatible with the cleaned DF)
def compute_momentum_series(df: pd.DataFrame, lookback: int = 60) -> pd.Series:
    close = df['Close'].astype(float)
    prev = close.shift(lookback)
    return (close / prev) - 1.0
