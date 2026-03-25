from __future__ import annotations


INDICATOR_LIBRARY = [
    {
        "slug": "ma",
        "name": "Moving Average",
        "short_name": "MA",
        "preview": "A smoothing tool that compresses noisy price movement into a visible trend line. It is the backbone of many trend-following systems, including Golden Cross.",
        "what_it_measures": "Moving averages smooth raw closing prices over a fixed window so trend direction becomes easier to read than on the raw candle chart alone.",
        "math_philosophy": "The core idea is signal extraction. A rolling mean filters high-frequency price noise and preserves slower-moving trend structure. Exponential variants push more weight onto the newest observations, which makes them more reactive.",
        "history": "Moving averages became widely adopted in technical charting as systematic trend-following matured through the twentieth century. They remain one of the most durable tools in discretionary and quantitative trading because they are simple, transparent, and easy to combine with other filters.",
        "significance": "For everyday traders, moving averages help answer a basic question: is the market drifting, trending, or reversing? They are often used for trend direction, pullback context, crossover systems, and dynamic support or resistance.",
        "implementation_ideas": [
            "Use a short-period MA to measure tactical trend speed and a long-period MA to measure structural trend direction.",
            "Compare SMA and EMA versions when you want to balance stability versus responsiveness.",
            "Treat MA slope and MA spread as supporting context instead of only trading the crossover itself.",
        ],
        "strategy_pairing": "Golden Cross is the canonical MA pairing. A faster average crossing above a slower average suggests trend acceleration. Adding volatility or momentum confirmation can improve timing.",
        "external_links": [
            {
                "title": "Wikipedia · Moving average",
                "url": "https://en.wikipedia.org/wiki/Moving_average",
                "preview": "Broad mathematical background on simple, cumulative, and weighted moving averages.",
            },
            {
                "title": "Investopedia · Moving Average",
                "url": "https://www.investopedia.com/terms/m/movingaverage.asp",
                "preview": "Trading-oriented explanation of how moving averages are used in trend analysis.",
            },
        ],
    },
    {
        "slug": "rsi",
        "name": "Relative Strength Index",
        "short_name": "RSI",
        "preview": "A bounded momentum oscillator that measures how persistent recent gains are relative to recent losses. It is commonly used to spot exhaustion, divergence, and pullback quality.",
        "what_it_measures": "RSI compares average up-closes to average down-closes over a lookback window and maps that ratio onto a 0 to 100 scale.",
        "math_philosophy": "RSI is less about trend direction than about speed and persistence. By bounding the output, it creates a stable frame for comparing different regimes and spotting overextended movement.",
        "history": "J. Welles Wilder introduced RSI in 1978 in 'New Concepts in Technical Trading Systems'. It became one of the most common oscillators because the interpretation framework is intuitive and portable across markets.",
        "significance": "RSI helps traders judge whether a move is stretched, healthy, or fading. It is especially useful when a trend strategy needs a momentum-quality filter rather than another trend line.",
        "implementation_ideas": [
            "Use RSI pullbacks during an existing uptrend instead of buying only after the oscillator becomes overbought.",
            "Track RSI divergence when price makes new highs but momentum weakens.",
            "Use custom thresholds instead of default 70/30 when the market stays persistently strong or weak.",
        ],
        "strategy_pairing": "RSI can supplement Golden Cross by filtering out late-stage breakouts. A bullish crossover paired with an RSI recovery from neutral can be cleaner than buying into already-exhausted momentum.",
        "external_links": [
            {
                "title": "Wikipedia · Relative strength index",
                "url": "https://en.wikipedia.org/wiki/Relative_strength_index",
                "preview": "Background on RSI construction, smoothing, and common interpretation ranges.",
            },
            {
                "title": "Investopedia · RSI",
                "url": "https://www.investopedia.com/terms/r/rsi.asp",
                "preview": "Trader-friendly overview of RSI signals, thresholds, and divergence use cases.",
            },
        ],
    },
    {
        "slug": "bbands",
        "name": "Bollinger Bands",
        "short_name": "BB",
        "preview": "A volatility envelope around a moving average. Narrow bands often hint at compression; widening bands often hint that a new move is underway.",
        "what_it_measures": "Bollinger Bands wrap a moving average with upper and lower bands placed a configurable number of standard deviations away from the center line.",
        "math_philosophy": "The indicator translates dispersion into a visual range. When the standard deviation contracts, the bands tighten; when volatility expands, the bands widen. That makes it useful for squeeze and breakout logic.",
        "history": "John Bollinger popularized the indicator in the 1980s as a practical way to combine trend and volatility context in one overlay.",
        "significance": "Bollinger Bands help traders frame whether price is quiet, stretched, mean-reverting, or expanding into a new trend. This is especially relevant in modern markets where regime changes in volatility often precede directional moves.",
        "implementation_ideas": [
            "Use bandwidth compression to identify a squeeze regime before a breakout.",
            "Track closes above the upper band as momentum confirmation, not automatically as a fade signal.",
            "Use the middle band as a practical trend retest or exit line.",
        ],
        "strategy_pairing": "This is the direct companion for the new Golden Cross Bollinger variants. Golden Cross answers trend direction; Bollinger squeeze and breakout behavior can improve timing and confirmation.",
        "external_links": [
            {
                "title": "Wikipedia · Bollinger Bands",
                "url": "https://en.wikipedia.org/wiki/Bollinger_Bands",
                "preview": "Overview of band construction, bandwidth, and interpretation.",
            },
            {
                "title": "Investopedia · Bollinger Bands",
                "url": "https://www.investopedia.com/terms/b/bollingerbands.asp",
                "preview": "Practical reading on squeezes, breakouts, and common misuse.",
            },
        ],
    },
    {
        "slug": "stoch",
        "name": "Stochastic Oscillator",
        "short_name": "Stoch",
        "preview": "A momentum oscillator that compares the closing price to the recent trading range. It is useful for timing shifts inside an existing trend or range.",
        "what_it_measures": "Stochastic tracks where the close sits relative to the recent high-low range, usually with a fast line (%K) and smoothed signal line (%D).",
        "math_philosophy": "Instead of focusing on absolute price change, stochastic measures position inside the local range. That makes it sensitive to shifts in buying or selling pressure before a full trend reversal is obvious.",
        "history": "George Lane developed the stochastic oscillator in the late 1950s. It remains popular because its range-based framing is intuitive and adaptive.",
        "significance": "The stochastic oscillator is useful when a trader wants to distinguish between a healthy pullback and momentum deterioration. It is commonly used in swing trading and range analysis.",
        "implementation_ideas": [
            "Watch for %K crossing %D out of oversold territory during an uptrend.",
            "Use range-bound markets to test stochastic reversals; use trending markets to test pullback continuation entries.",
            "Adjust the smoothing periods if the default signals feel too noisy for the asset.",
        ],
        "strategy_pairing": "Stochastic can act as a timing layer on top of Golden Cross. Once the structural trend is bullish, stochastic can help locate higher-quality pullback entries rather than blindly buying every breakout.",
        "external_links": [
            {
                "title": "Wikipedia · Stochastic oscillator",
                "url": "https://en.wikipedia.org/wiki/Stochastic_oscillator",
                "preview": "Math and signal construction details for %K, %D, and smoothing variants.",
            },
            {
                "title": "Investopedia · Stochastic Oscillator",
                "url": "https://www.investopedia.com/terms/s/stochasticoscillator.asp",
                "preview": "Applied explanation of overbought, oversold, and crossover signals.",
            },
        ],
    },
    {
        "slug": "adx",
        "name": "Average Directional Index",
        "short_name": "ADX",
        "preview": "A trend-strength measure that helps answer whether a market is truly trending or just moving sideways with noise.",
        "what_it_measures": "ADX is built from directional movement. It quantifies how strong the trend is, while +DI and -DI indicate which side currently has directional control.",
        "math_philosophy": "ADX separates trend strength from trend direction. That distinction matters because a rising market is not always a strong trend, and a strong trend is not always bullish.",
        "history": "ADX was also introduced by J. Welles Wilder in 1978 as part of his directional movement system.",
        "significance": "ADX is valuable when a trend-following strategy needs to avoid weak, choppy regimes. It helps filter breakouts or crossovers that happen in low-quality conditions.",
        "implementation_ideas": [
            "Require ADX above a threshold before accepting a trend-following signal.",
            "Use +DI versus -DI to see which side has directional control once ADX confirms strength.",
            "Treat a rising ADX after consolidation as evidence that a new directional move may be becoming real.",
        ],
        "strategy_pairing": "ADX can improve Golden Cross by filtering out low-quality crosses that occur in sideways markets. A bullish crossover with strengthening ADX is usually more persuasive than a crossover with flat ADX.",
        "external_links": [
            {
                "title": "Wikipedia · Average directional movement index",
                "url": "https://en.wikipedia.org/wiki/Average_directional_movement_index",
                "preview": "Directional movement background for ADX, +DI, and -DI.",
            },
            {
                "title": "Investopedia · ADX",
                "url": "https://www.investopedia.com/terms/a/adx.asp",
                "preview": "Practical interpretation of trend thresholds and direction filters.",
            },
        ],
    },
    {
        "slug": "ichimoku",
        "name": "Ichimoku Cloud",
        "short_name": "Ichimoku",
        "preview": "A multi-line trend framework that combines support, resistance, momentum, and forward-looking context in one visual structure.",
        "what_it_measures": "Ichimoku combines conversion, base, leading spans, and lagging span to frame trend direction, momentum balance, and projected support/resistance zones.",
        "math_philosophy": "Ichimoku is less a single indicator and more a complete visual system. It blends different rolling midpoints and time shifts to create a structural view of the market.",
        "history": "Goichi Hosoda developed Ichimoku in Japan and published the method in the twentieth century. It became globally popular because it provides a full market-structure read in one overlay.",
        "significance": "Ichimoku is useful for traders who want more context than a single average or oscillator can provide. The cloud, base line, and conversion line together can frame trend quality and likely reaction zones.",
        "implementation_ideas": [
            "Use cloud direction and price location relative to the cloud as a structural filter.",
            "Track conversion/base line crosses as tactical triggers inside the bigger trend context.",
            "Use Span A and Span B as projected support/resistance rather than as exact reversal points.",
        ],
        "strategy_pairing": "Ichimoku can supplement Golden Cross by clarifying whether the crossover is happening above or below broader structural support. A Golden Cross above a rising cloud usually reads stronger than one inside a noisy cloud.",
        "external_links": [
            {
                "title": "Wikipedia · Ichimoku Kinko Hyo",
                "url": "https://en.wikipedia.org/wiki/Ichimoku_Kink%C5%8D_Hy%C5%8D",
                "preview": "Conceptual and historical background for the cloud framework.",
            },
            {
                "title": "Investopedia · Ichimoku Cloud",
                "url": "https://www.investopedia.com/terms/i/ichimoku-cloud.asp",
                "preview": "Readable summary of the lines, cloud, and common trading use cases.",
            },
        ],
    },
    {
        "slug": "psar",
        "name": "Parabolic SAR",
        "short_name": "PSAR",
        "preview": "A trend-following stop-and-reversal indicator that places trailing dots above or below price to show directional bias and stop movement.",
        "what_it_measures": "Parabolic SAR marks a trailing stop path that accelerates as a trend extends, flipping when price crosses the projected stop level.",
        "math_philosophy": "PSAR is about trade management as much as trend identification. The acceleration factor makes the stop tighten as a move persists, which forces the model to eventually exit or reverse.",
        "history": "J. Welles Wilder introduced Parabolic SAR in 1978. It is most often used as a stop or trailing-bias overlay rather than as a standalone trading system.",
        "significance": "PSAR helps traders visualize where a systematic trailing stop would sit. That makes it useful for exit discipline, especially in fast-moving trends where discretionary stop placement drifts.",
        "implementation_ideas": [
            "Use PSAR as a trailing exit line rather than an entry trigger by itself.",
            "Compare PSAR flips to your existing exit logic to see whether it would have reduced drawdowns or exited too early.",
            "Combine PSAR with a trend filter like Golden Cross or ADX to avoid whipsaw-heavy sideways markets.",
        ],
        "strategy_pairing": "PSAR is a natural supplement to Golden Cross when the entry logic is already trend-based and the missing piece is a disciplined trailing exit.",
        "external_links": [
            {
                "title": "Investopedia · Parabolic SAR",
                "url": "https://www.investopedia.com/terms/p/parabolicindicator.asp",
                "preview": "Overview of acceleration, stop placement, and trend-following use.",
            },
        ],
    },
    {
        "slug": "obv",
        "name": "On-Balance Volume",
        "short_name": "OBV",
        "preview": "A cumulative volume measure designed to show whether volume is flowing in the same direction as price or quietly diverging from it.",
        "what_it_measures": "OBV adds volume on up-closes and subtracts volume on down-closes, producing a cumulative pressure line that can confirm or question price action.",
        "math_philosophy": "The indicator treats volume as conviction. If price rises while OBV rises too, the move may have broader participation. If price rises but OBV lags, the move may be weaker than it appears.",
        "history": "Joseph Granville popularized OBV in the 1960s as part of a broader emphasis on volume-led analysis.",
        "significance": "OBV helps traders avoid relying on price alone. It is particularly useful for confirming breakouts, distribution, and hidden accumulation behavior.",
        "implementation_ideas": [
            "Use OBV trend direction as confirmation for breakouts or moving-average signals.",
            "Compare OBV to its own signal average to smooth noisy swings.",
            "Watch for OBV divergence when price is still making highs but participation is fading.",
        ],
        "strategy_pairing": "OBV is a volume-confirmation layer for Golden Cross. A bullish crossover with improving OBV often reads stronger than a crossover that happens on weak participation.",
        "external_links": [
            {
                "title": "Wikipedia · On-balance volume",
                "url": "https://en.wikipedia.org/wiki/On-balance_volume",
                "preview": "Background on cumulative volume logic and confirmation theory.",
            },
            {
                "title": "Investopedia · OBV",
                "url": "https://www.investopedia.com/terms/o/onbalancevolume.asp",
                "preview": "Trading-oriented explanation of volume confirmation and divergence.",
            },
        ],
    },
]


def get_indicator_library() -> list[dict]:
    return [dict(item) for item in INDICATOR_LIBRARY]


def get_indicator_map() -> dict[str, dict]:
    return {item["slug"]: dict(item) for item in INDICATOR_LIBRARY}
