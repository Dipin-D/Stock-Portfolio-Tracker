from __future__ import annotations

import pandas as pd

from my_app.backtesting.metrics import calculate_trade_metrics

from .base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    slug = "momentum_12m"
    name = "Momentum 12M"
    category = "Trend"
    description = "12-month price momentum evidence stream using configurable thresholds."
    default_params = {
        "lookback": 252,
        "buy_threshold": 0.0,
        "exit_threshold": -0.02,
        "order_percentage": 100,
        "starting_cash": 100000,
        "override_shares": None,
    }
    signal_family = "trend"

    def compute_features(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        configured = self.normalize_params(params)
        lookback = int(configured["lookback"])
        enriched = df.copy()
        enriched["momentum_signal"] = enriched["Close"].pct_change(lookback)
        return enriched

    def generate_signal(self, df: pd.DataFrame, params: dict) -> pd.Series:
        configured = self.normalize_params(params)
        return df["momentum_signal"] > float(configured["buy_threshold"])

    def signal_strength(self, df: pd.DataFrame, params: dict) -> pd.Series:
        strength = ((df["momentum_signal"] + 0.10) / 0.40).clip(lower=0, upper=1)
        return strength.fillna(0)

    def describe_signal_math(
        self,
        df: pd.DataFrame,
        params: dict,
        signal_series: pd.Series,
        strength_series: pd.Series,
    ) -> dict:
        configured = self.normalize_params(params)
        momentum_values = pd.to_numeric(df["momentum_signal"], errors="coerce").dropna()
        momentum_value = float(momentum_values.iloc[-1]) if not momentum_values.empty else 0.0

        return {
            "signal_formula": "signal = lookback_return > buy_threshold",
            "strength_formula": "strength = clamp((lookback_return + 0.10) / 0.40, 0, 1)",
            "signal_active": self.latest_boolean(signal_series),
            "strength": self.latest_float(strength_series),
            "inputs": {
                "lookback_days": int(configured["lookback"]),
                "lookback_return": momentum_value,
                "buy_threshold": float(configured["buy_threshold"]),
                "shift": 0.10,
                "range": 0.40,
            },
            "display_rows": [
                {"label": f"Lookback ({int(configured['lookback'])}d)", "value": momentum_value, "display": f"{momentum_value:.4f}"},
                {"label": "Buy threshold", "value": float(configured["buy_threshold"]), "display": f"{float(configured['buy_threshold']):.4f}"},
                {"label": "Shift", "value": 0.10, "display": "0.1000"},
                {"label": "Range", "value": 0.40, "display": "0.4000"},
            ],
        }

    def backtest(self, df: pd.DataFrame, params: dict) -> dict:
        configured = self.normalize_params(params)
        buy_threshold = float(configured["buy_threshold"])
        exit_threshold = float(configured["exit_threshold"])
        starting_cash = float(configured["starting_cash"])
        order_percentage = float(configured["order_percentage"]) / 100.0
        override_shares = configured.get("override_shares")

        cash = starting_cash
        shares = 0
        open_trade = None
        trades: list[dict] = []
        equity_curve: list[dict] = []
        momentum = df["momentum_signal"]

        for index, row in df.iterrows():
            price = float(row["Close"])
            timestamp = int(row["Date"])
            date_text = row["Date_dt"].date().isoformat()
            previous_momentum = momentum.shift(1).loc[index]
            current_momentum = momentum.loc[index]

            if pd.notna(previous_momentum) and pd.notna(current_momentum):
                if shares == 0 and previous_momentum <= buy_threshold and current_momentum > buy_threshold:
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

                elif shares > 0 and previous_momentum >= exit_threshold and current_momentum < exit_threshold and open_trade:
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

        if open_trade and shares > 0:
            last_price = float(df.iloc[-1]["Close"])
            last_date = df.iloc[-1]["Date_dt"].date().isoformat()
            cash += shares * last_price
            pnl = (last_price - open_trade["entry_price"]) * shares
            return_pct = (last_price / open_trade["entry_price"]) - 1 if open_trade["entry_price"] else 0.0
            trades.append({
                **open_trade,
                "exit_date": last_date,
                "exit_price": last_price,
                "pnl": pnl,
                "return_pct": return_pct,
                "outcome": "win" if pnl >= 0 else "loss",
            })
            if equity_curve:
                equity_curve[-1]["value"] = float(cash)

        metrics = calculate_trade_metrics(trades, starting_cash, cash, equity_curve)
        return {
            "trades": trades,
            "metrics": metrics,
            "equity_curve": equity_curve,
            "final_cash": float(cash),
        }
