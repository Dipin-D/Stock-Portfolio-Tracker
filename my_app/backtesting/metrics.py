from __future__ import annotations

from statistics import mean


def calculate_max_drawdown(equity_curve: list[dict]) -> float:
    if not equity_curve:
        return 0.0

    peak = equity_curve[0]["value"]
    max_drawdown = 0.0
    for point in equity_curve:
        value = point["value"]
        if value > peak:
            peak = value
        if peak:
            drawdown = (value - peak) / peak
            max_drawdown = min(max_drawdown, drawdown)
    return float(max_drawdown)


def calculate_trade_metrics(
    trades: list[dict],
    starting_cash: float,
    final_cash: float,
    equity_curve: list[dict] | None = None,
) -> dict:
    wins = [trade for trade in trades if (trade.get("pnl") or 0) >= 0]
    losses = [trade for trade in trades if (trade.get("pnl") or 0) < 0]
    trade_returns = [trade.get("return_pct", 0.0) for trade in trades]
    trade_pnls = [trade.get("pnl", 0.0) for trade in trades]
    trade_count = len(trades)
    win_rate = (len(wins) / trade_count) if trade_count else 0.0
    total_return = ((final_cash - starting_cash) / starting_cash) if starting_cash else 0.0

    return {
        "trade_count": trade_count,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": float(win_rate),
        "avg_trade_return": float(mean(trade_returns)) if trade_returns else 0.0,
        "avg_trade_pnl": float(mean(trade_pnls)) if trade_pnls else 0.0,
        "total_return_pct": float(total_return),
        "max_drawdown": calculate_max_drawdown(equity_curve or []),
        "starting_cash": float(starting_cash),
        "final_cash": float(final_cash),
    }

