from __future__ import annotations

import pandas as pd

from my_app.backtesting.metrics import calculate_trade_metrics

from .base import BaseStrategy


class GoldenCrossStrategy(BaseStrategy):
    slug = "golden_cross"
    name = "Golden Cross"
    category = "Trend"
    description = "Fast SMA crossing above slow SMA. In Bayesian mode it acts as one trend evidence source."
    default_params = {
        "fast_sma": 50,
        "slow_sma": 200,
        "order_percentage": 100,
        "starting_cash": 100000,
        "override_shares": None,
    }
    signal_family = "trend"

    def compute_features(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        configured = self.normalize_params(params)
        fast_period = int(configured["fast_sma"])
        slow_period = int(configured["slow_sma"])
        enriched = df.copy()
        enriched["gc_fast"] = enriched["Close"].rolling(fast_period).mean()
        enriched["gc_slow"] = enriched["Close"].rolling(slow_period).mean()
        return enriched

    def generate_signal(self, df: pd.DataFrame, params: dict) -> pd.Series:
        return df["gc_fast"] > df["gc_slow"]

    def signal_strength(self, df: pd.DataFrame, params: dict) -> pd.Series:
        spread = ((df["gc_fast"] - df["gc_slow"]) / df["gc_slow"].replace(0, pd.NA)).clip(lower=0)
        return (spread / 0.15).clip(lower=0, upper=1).fillna(0)

    def describe_signal_math(
        self,
        df: pd.DataFrame,
        params: dict,
        signal_series: pd.Series,
        strength_series: pd.Series,
    ) -> dict:
        configured = self.normalize_params(params)
        latest = df[["gc_fast", "gc_slow"]].dropna().tail(1)
        if latest.empty:
            fast_ma = slow_ma = spread_ratio = 0.0
        else:
            row = latest.iloc[0]
            fast_ma = float(row["gc_fast"])
            slow_ma = float(row["gc_slow"])
            spread_ratio = max(((fast_ma - slow_ma) / slow_ma), 0.0) if slow_ma else 0.0

        return {
            "signal_formula": "signal = fast_ma > slow_ma",
            "strength_formula": "strength = clamp(max((fast_ma - slow_ma) / slow_ma, 0) / 0.15, 0, 1)",
            "signal_active": self.latest_boolean(signal_series),
            "strength": self.latest_float(strength_series),
            "inputs": {
                "fast_sma_period": int(configured["fast_sma"]),
                "slow_sma_period": int(configured["slow_sma"]),
                "fast_ma": fast_ma,
                "slow_ma": slow_ma,
                "spread_ratio": spread_ratio,
                "normalizer": 0.15,
            },
            "display_rows": [
                {"label": f"Fast SMA ({int(configured['fast_sma'])})", "value": fast_ma, "display": f"{fast_ma:.4f}"},
                {"label": f"Slow SMA ({int(configured['slow_sma'])})", "value": slow_ma, "display": f"{slow_ma:.4f}"},
                {"label": "Spread ratio", "value": spread_ratio, "display": f"{spread_ratio:.4f}"},
                {"label": "Normalizer", "value": 0.15, "display": "0.1500"},
            ],
        }

    def backtest(self, df: pd.DataFrame, params: dict) -> dict:
        configured = self.normalize_params(params)
        fast = df["gc_fast"]
        slow = df["gc_slow"]
        previous_fast = fast.shift(1)
        previous_slow = slow.shift(1)
        buy_signal = (previous_fast < previous_slow) & (fast >= slow)
        sell_signal = (previous_fast > previous_slow) & (fast <= slow)

        starting_cash = float(configured["starting_cash"])
        order_percentage = float(configured["order_percentage"]) / 100.0
        override_shares = configured.get("override_shares")

        cash = starting_cash
        shares = 0
        open_trade = None
        cash_before_last_buy = cash
        trades: list[dict] = []
        equity_curve: list[dict] = []

        for _, row in df.iterrows():
            price = float(row["Close"])
            timestamp = int(row["Date"])
            date_text = row["Date_dt"].date().isoformat()

            if shares == 0 and bool(buy_signal.loc[row.name]):
                cash_before_last_buy = cash
                requested_shares = int(override_shares) if override_shares not in (None, "", "Auto") else int((cash * order_percentage) // price)
                if requested_shares > 0:
                    shares = requested_shares
                    cash -= shares * price
                    open_trade = {
                        "strategy_slug": self.slug,
                        "entry_date": date_text,
                        "entry_price": price,
                        "shares": shares,
                    }

            elif shares > 0 and bool(sell_signal.loc[row.name]) and open_trade:
                cash += shares * price
                pnl = (price - open_trade["entry_price"]) * shares
                return_pct = (price / open_trade["entry_price"]) - 1 if open_trade["entry_price"] else 0.0
                trades.append({
                    **open_trade,
                    "exit_date": date_text,
                    "exit_price": price,
                    "pnl": pnl,
                    "return_pct": return_pct,
                    "outcome": "win" if pnl >= 0 else "loss",
                })
                shares = 0
                open_trade = None

            equity_curve.append({
                "time": timestamp,
                "value": float(cash + shares * price),
            })

        if open_trade:
            cash = cash_before_last_buy
            if equity_curve:
                equity_curve[-1]["value"] = float(cash)

        metrics = calculate_trade_metrics(trades, starting_cash, cash, equity_curve)
        return {
            "trades": trades,
            "metrics": metrics,
            "equity_curve": equity_curve,
            "final_cash": float(cash),
        }
