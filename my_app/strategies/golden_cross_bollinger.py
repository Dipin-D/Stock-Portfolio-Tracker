from __future__ import annotations

import pandas as pd

from my_app.backtesting.metrics import calculate_trade_metrics

from .base import BaseStrategy


class _GoldenCrossBollingerBaseStrategy(BaseStrategy):
    category = "Trend + Volatility"
    signal_family = "trend"
    default_params = {
        "fast_sma": 50,
        "slow_sma": 200,
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "squeeze_lookback": 20,
        "squeeze_quantile": 0.35,
        "order_percentage": 100,
        "starting_cash": 100000,
        "override_shares": None,
    }

    def compute_features(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        configured = self.normalize_params(params)
        fast_period = int(configured["fast_sma"])
        slow_period = int(configured["slow_sma"])
        bb_period = int(configured["bb_period"])
        squeeze_lookback = int(configured["squeeze_lookback"])
        std_dev = float(configured["bb_std_dev"])
        quantile = float(configured["squeeze_quantile"])

        enriched = df.copy()
        enriched["gc_fast"] = enriched["Close"].rolling(fast_period).mean()
        enriched["gc_slow"] = enriched["Close"].rolling(slow_period).mean()
        enriched["bb_mid"] = enriched["Close"].rolling(bb_period).mean()
        rolling_std = enriched["Close"].rolling(bb_period).std()
        enriched["bb_upper"] = enriched["bb_mid"] + (rolling_std * std_dev)
        enriched["bb_lower"] = enriched["bb_mid"] - (rolling_std * std_dev)
        enriched["bb_width"] = (
            (enriched["bb_upper"] - enriched["bb_lower"]) /
            enriched["bb_mid"].replace(0, pd.NA)
        )
        enriched["bb_width_threshold"] = (
            enriched["bb_width"]
            .rolling(squeeze_lookback)
            .quantile(quantile)
        )
        enriched["squeeze_active"] = (
            enriched["bb_width"] <= enriched["bb_width_threshold"]
        ).fillna(False)
        enriched["recent_squeeze"] = (
            enriched["squeeze_active"]
            .shift(1)
            .rolling(3)
            .max()
            .fillna(0)
            .astype(bool)
        )
        enriched["gc_active"] = (enriched["gc_fast"] > enriched["gc_slow"]).fillna(False)
        enriched["bb_expanding"] = (enriched["bb_width"] > enriched["bb_width"].shift(1)).fillna(False)
        enriched["base_breakout"] = (
            enriched["gc_active"] &
            enriched["recent_squeeze"] &
            (enriched["Close"] > enriched["bb_mid"]) &
            enriched["bb_expanding"]
        ).fillna(False)
        enriched["strict_breakout"] = (
            enriched["base_breakout"] &
            (enriched["Close"] > enriched["bb_upper"])
        ).fillna(False)
        return enriched

    def signal_strength(self, df: pd.DataFrame, params: dict) -> pd.Series:
        gc_spread = ((df["gc_fast"] - df["gc_slow"]) / df["gc_slow"].replace(0, pd.NA)).clip(lower=0)
        band_distance = ((df["Close"] - df["bb_mid"]) / df["bb_mid"].replace(0, pd.NA)).clip(lower=0)
        width_expansion = ((df["bb_width"] - df["bb_width_threshold"]) / df["bb_width_threshold"].replace(0, pd.NA)).clip(lower=0)
        strict_band_distance = ((df["Close"] - df["bb_upper"]) / df["bb_upper"].replace(0, pd.NA)).clip(lower=0)
        strength = (
            0.45 * (gc_spread / 0.15).clip(0, 1).fillna(0)
            + 0.30 * (band_distance / 0.08).clip(0, 1).fillna(0)
            + 0.15 * (width_expansion / 0.60).clip(0, 1).fillna(0)
            + 0.10 * (strict_band_distance / 0.05).clip(0, 1).fillna(0)
        )
        return strength.clip(0, 1)

    def _entry_signal(self, df: pd.DataFrame) -> pd.Series:
        raise NotImplementedError

    def generate_signal(self, df: pd.DataFrame, params: dict) -> pd.Series:
        return self._entry_signal(df)

    def describe_signal_math(
        self,
        df: pd.DataFrame,
        params: dict,
        signal_series: pd.Series,
        strength_series: pd.Series,
    ) -> dict:
        configured = self.normalize_params(params)
        latest = df[[
            "gc_fast",
            "gc_slow",
            "bb_mid",
            "bb_upper",
            "bb_width",
            "bb_width_threshold",
            "recent_squeeze",
            "base_breakout",
            "strict_breakout",
        ]].dropna().tail(1)

        if latest.empty:
            fast_ma = slow_ma = bb_mid = bb_upper = width = width_threshold = 0.0
            recent_squeeze = False
            base_breakout = False
            strict_breakout = False
        else:
            row = latest.iloc[0]
            fast_ma = float(row["gc_fast"])
            slow_ma = float(row["gc_slow"])
            bb_mid = float(row["bb_mid"])
            bb_upper = float(row["bb_upper"])
            width = float(row["bb_width"])
            width_threshold = float(row["bb_width_threshold"])
            recent_squeeze = bool(row["recent_squeeze"])
            base_breakout = bool(row["base_breakout"])
            strict_breakout = bool(row["strict_breakout"])

        return {
            "signal_formula": self.signal_formula,
            "strength_formula": (
                "strength = 0.45 * gc_spread_norm + 0.30 * middle_band_breakout_norm "
                "+ 0.15 * width_expansion_norm + 0.10 * upper_band_breakout_norm"
            ),
            "signal_active": self.latest_boolean(signal_series),
            "strength": self.latest_float(strength_series),
            "inputs": {
                "fast_sma_period": int(configured["fast_sma"]),
                "slow_sma_period": int(configured["slow_sma"]),
                "bb_period": int(configured["bb_period"]),
                "bb_std_dev": float(configured["bb_std_dev"]),
                "squeeze_lookback": int(configured["squeeze_lookback"]),
                "squeeze_quantile": float(configured["squeeze_quantile"]),
                "fast_ma": fast_ma,
                "slow_ma": slow_ma,
                "bb_mid": bb_mid,
                "bb_upper": bb_upper,
                "band_width": width,
                "band_width_threshold": width_threshold,
                "recent_squeeze": recent_squeeze,
                "base_breakout": base_breakout,
                "strict_breakout": strict_breakout,
            },
            "display_rows": [
                {"label": f"Fast SMA ({int(configured['fast_sma'])})", "value": fast_ma, "display": f"{fast_ma:.4f}"},
                {"label": f"Slow SMA ({int(configured['slow_sma'])})", "value": slow_ma, "display": f"{slow_ma:.4f}"},
                {"label": "Bollinger middle band", "value": bb_mid, "display": f"{bb_mid:.4f}"},
                {"label": "Bollinger upper band", "value": bb_upper, "display": f"{bb_upper:.4f}"},
                {"label": "Band width", "value": width, "display": f"{width:.4f}"},
                {"label": "Width threshold", "value": width_threshold, "display": f"{width_threshold:.4f}"},
                {"label": "Recent squeeze", "value": recent_squeeze, "display": "Yes" if recent_squeeze else "No"},
                {"label": "Base breakout", "value": base_breakout, "display": "Yes" if base_breakout else "No"},
                {"label": "Strict breakout", "value": strict_breakout, "display": "Yes" if strict_breakout else "No"},
            ],
        }

    def backtest(self, df: pd.DataFrame, params: dict, runtime_context: dict | None = None) -> dict:
        configured = self.normalize_params(params)
        entry_signal = self._entry_signal(df)
        exit_signal = (
            (df["Close"] < df["bb_mid"]) |
            (~df["gc_active"])
        ).fillna(False)
        entry_allowed = self.entry_allowed_mask(df, runtime_context)

        buy_signal = (~entry_signal.shift(1).fillna(False)) & entry_signal.fillna(False)
        sell_signal = (~exit_signal.shift(1).fillna(False)) & exit_signal.fillna(False)

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

            if shares == 0 and bool(buy_signal.loc[row.name]) and bool(entry_allowed.loc[row.name]):
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


class GoldenCrossBollingerSqueezeStrategy(_GoldenCrossBollingerBaseStrategy):
    slug = "golden_cross_bollinger_squeeze"
    name = "Golden Cross + Bollinger Squeeze"
    description = "Golden Cross trend filter with a Bollinger squeeze expansion breakout above the middle band."
    signal_formula = (
        "signal = golden_cross_active and recent_squeeze and close > bollinger_middle_band "
        "and band_width > previous_band_width"
    )

    def _entry_signal(self, df: pd.DataFrame) -> pd.Series:
        return df["base_breakout"].fillna(False)


class GoldenCrossBollingerBreakoutConfirmStrategy(_GoldenCrossBollingerBaseStrategy):
    slug = "golden_cross_bollinger_breakout_confirm"
    name = "Golden Cross + Bollinger Breakout Confirm"
    description = "Golden Cross trend filter with a Bollinger squeeze breakout plus explicit upper-band confirmation."
    signal_formula = (
        "signal = base_breakout and close > bollinger_upper_band"
    )

    def _entry_signal(self, df: pd.DataFrame) -> pd.Series:
        return df["strict_breakout"].fillna(False)
