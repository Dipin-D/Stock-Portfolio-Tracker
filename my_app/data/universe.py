DEFAULT_BACKTEST_UNIVERSE = [
    "SPY",
    "QQQ",
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "GOOGL",
]

DEFAULT_WATCHLIST_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "AMD", "NFLX",
    "CRM", "ADBE", "COST", "PEP", "SPY", "QQQ", "IWM", "SMH", "XLE", "XLF", "XLY", "XLV", "XLC", "ARKK",
]


def build_training_universe(ticker: str, benchmark: str) -> list[str]:
    symbols: list[str] = []
    for candidate in [benchmark, ticker, *DEFAULT_BACKTEST_UNIVERSE]:
        normalized = (candidate or "").upper().strip()
        if normalized and normalized not in symbols:
            symbols.append(normalized)
    return symbols


def get_watchlist_universe() -> list[str]:
    return list(DEFAULT_WATCHLIST_UNIVERSE)
