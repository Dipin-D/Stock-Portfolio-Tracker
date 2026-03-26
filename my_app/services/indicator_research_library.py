from __future__ import annotations

from copy import deepcopy


INDICATOR_RESEARCH_LIBRARY = {
    "ma": {
        "research_stats": [
            "Stepwise SPA studies report strong in-sample candidates but weak out-of-sample persistence for moving-average rule families.",
            "High-frequency stationary MA variants reached about 48.84% annual return and 2.17 Sharpe before costs in one study, but profits disappeared after realistic trading costs.",
            "Long-horizon rule tests show conditional return differences between MA buy and sell regimes, but later replication work found little robust predictive persistence.",
        ],
        "research_papers": [
            {
                "title": "Brock, Lakonishok, LeBaron (1992) - Simple Technical Trading Rules and the Stochastic Properties of Stock Returns",
                "abstract": "Tests moving-average and trading-range-break rules on long Dow history and finds statistically different return distributions across rule states, challenging a pure random-walk baseline.",
                "key_stat": "Documents persistent buy-vs-sell regime return separation in the historical sample.",
                "url": "https://scholar.google.com/scholar?q=Brock+Lakonishok+LeBaron+1992+technical+trading+rules",
            },
            {
                "title": "Sullivan, Timmermann, White (1999) - Data-Snooping, Technical Trading Rule Performance, and the Bootstrap",
                "abstract": "Shows that searching across large technical-rule universes can manufacture false positives; introduces robust bootstrap framing for data-snooping control.",
                "key_stat": "Large rule universes materially inflate false discovery risk without correction.",
                "url": "https://scholar.google.com/scholar?q=Sullivan+Timmermann+White+1999+data+snooping+technical+trading",
            },
            {
                "title": "Stepwise SPA Multi-Market Technical Rules Study",
                "abstract": "Applies superior predictive ability controls across many markets and rule families; finds that apparent in-sample winners often fail to stay superior out-of-sample.",
                "key_stat": "Reported best in-sample excess Sharpe values can exceed 1.0 in select markets but typically do not persist after costs and forward testing.",
                "url": "https://scholar.google.com/scholar?q=stepwise+SPA+technical+trading+rules+out+of+sample",
            },
            {
                "title": "Out-of-Sample Recheck of Best Historical Technical Rules",
                "abstract": "Re-tests previously successful simple rules on fresh samples and reports little evidence of durable predictability.",
                "key_stat": "Shows many celebrated historical MA settings fail on later data windows.",
                "url": "https://scholar.google.com/scholar?q=out+of+sample+best+technical+trading+rules+no+predictability",
            },
        ],
        "math_philosophy_papers": [
            {
                "title": "White (2000) - A Reality Check for Data Snooping",
                "summary": "Formalizes why optimization across many technical-rule candidates overstates significance and proposes corrected inference.",
                "url": "https://scholar.google.com/scholar?q=White+2000+Reality+Check+for+Data+Snooping",
            },
            {
                "title": "Hansen (2005) - A Test for Superior Predictive Ability",
                "summary": "Provides a stronger framework than naive best-rule selection when many competing forecasts or rule sets are compared.",
                "url": "https://scholar.google.com/scholar?q=Hansen+2005+Superior+Predictive+Ability",
            },
            {
                "title": "Bailey et al. (2014) - Probability of Backtest Overfitting",
                "summary": "Quantifies how often selected top backtests are statistical mirages under broad parameter search.",
                "url": "https://scholar.google.com/scholar?q=Probability+of+Backtest+Overfitting+Bailey",
            },
        ],
        "youtube_tutorials": [
            {
                "title": "SMA vs EMA technical tutorial",
                "focus": "Compare smoothing behavior, lag, and crossover interpretation.",
                "url": "https://www.youtube.com/results?search_query=SMA+vs+EMA+trading+tutorial",
            },
            {
                "title": "Moving average crossover strategy walkthrough",
                "focus": "Practical implementation and common whipsaw mistakes.",
                "url": "https://www.youtube.com/results?search_query=moving+average+crossover+strategy+tutorial",
            },
        ],
    },
    "rsi": {
        "research_stats": [
            "A cross-index 2007-2012 oscillator study reported RSI outperformance versus buy-and-hold in some markets, including about 14.67% annualized versus -5.91% in one Japanese index sample.",
            "ETF-focused evidence found weaker RSI robustness, with about 2.46% average annual return versus roughly 6.01% buy-and-hold across tested ETFs.",
            "Large multi-market studies still show RSI rule persistence degrades out-of-sample after transaction costs and multiple-testing controls.",
        ],
        "research_papers": [
            {
                "title": "Cross-Index Oscillator Comparison (RSI, MACD, Stochastic, PSAR)",
                "abstract": "Compares oscillator families net of commissions across major equity indices and finds performance is highly market and regime dependent.",
                "key_stat": "Reports one strong RSI sample at around 14.67% annualized versus -5.91% buy-and-hold.",
                "url": "https://scholar.google.com/scholar?q=RSI+MACD+Stochastic+Parabolic+SAR+2007+2012+indices",
            },
            {
                "title": "Southeast Asian Technical Rule Study (2000-2013)",
                "abstract": "Tests several indicators, including RSI, across five markets with transaction costs and shows many apparent gains weaken materially net of costs.",
                "key_stat": "RSI frequently underperformed stronger alternatives like STOCH-D or MACD in that sample.",
                "url": "https://scholar.google.com/scholar?q=Southeast+Asian+markets+RSI+technical+analysis+2000+2013",
            },
            {
                "title": "ETF Indicator Performance Comparison",
                "abstract": "Evaluates indicator-only systems on ETF universes and shows RSI has inconsistent standalone edge relative to passive exposure.",
                "key_stat": "Average annual RSI performance near 2.46% versus about 6.01% buy-and-hold in the study summary.",
                "url": "https://scholar.google.com/scholar?q=ETF+RSI+strategy+buy+and+hold+comparison",
            },
        ],
        "math_philosophy_papers": [
            {
                "title": "Wilder (1978) - New Concepts in Technical Trading Systems",
                "summary": "Original RSI and ADX/PSAR framework; foundational for smoothing logic and bounded momentum interpretation.",
                "url": "https://scholar.google.com/scholar?q=New+Concepts+in+Technical+Trading+Systems+Wilder",
            },
            {
                "title": "White (2000) - Reality Check",
                "summary": "Explains why optimized RSI thresholds without correction are statistically unreliable.",
                "url": "https://scholar.google.com/scholar?q=White+2000+Reality+Check+for+Data+Snooping",
            },
            {
                "title": "Hansen (2005) - Superior Predictive Ability",
                "summary": "Useful for screening many RSI parameter sets while controlling false discoveries.",
                "url": "https://scholar.google.com/scholar?q=Hansen+2005+Superior+Predictive+Ability",
            },
        ],
        "youtube_tutorials": [
            {
                "title": "RSI full indicator deep dive",
                "focus": "RSI formula intuition and interpretation in trend vs range.",
                "url": "https://www.youtube.com/results?search_query=RSI+indicator+deep+dive+tutorial",
            },
            {
                "title": "How to use RSI in trading",
                "focus": "Beginner workflow for signal confirmation and threshold use.",
                "url": "https://www.youtube.com/results?search_query=how+to+use+RSI+for+trading",
            },
        ],
    },
    "bbands": {
        "research_stats": [
            "Peer-reviewed BB tests across major markets show standard rules often fail to beat buy-and-hold once realistic costs are applied.",
            "Contrarian BB variants can outperform plain breakout variants in select regimes.",
            "A high-frequency study reported about 59.31% annualized return and 2.33 Sharpe in a best pre-cost BB setup, but profitability collapsed after costs.",
        ],
        "research_papers": [
            {
                "title": "Bollinger Bands Profitability Across Equity Markets",
                "abstract": "Evaluates classical Bollinger settings and strategy variants and finds baseline rules are fragile net of costs; variant design and regime context are decisive.",
                "key_stat": "Standard BB strategies generally underperform cost-adjusted buy-and-hold in tested samples.",
                "url": "https://scholar.google.com/scholar?q=Bollinger+Bands+profitability+transaction+costs",
            },
            {
                "title": "Popularity versus Profitability of Bollinger Bands",
                "abstract": "Shows BB predictability can exist in long samples but profitability declines over time, consistent with adaptive-market dynamics.",
                "key_stat": "Documents meaningful time decay in BB edge across subperiods.",
                "url": "https://scholar.google.com/scholar?q=popularity+versus+profitability+Bollinger+Bands",
            },
            {
                "title": "Moving Average Envelopes versus Bollinger Bands (Hong Kong)",
                "abstract": "Compares fixed-envelope and volatility-adjusted bands and finds BB do not automatically dominate simpler alternatives in all settings.",
                "key_stat": "Highlights indicator-choice sensitivity to market microstructure and regime.",
                "url": "https://scholar.google.com/scholar?q=Moving+Average+Envelopes+versus+Bollinger+Bands+Hong+Kong",
            },
        ],
        "math_philosophy_papers": [
            {
                "title": "Rolling Volatility and Band Width as Non-Stationary Estimators",
                "summary": "Frames BB as moving z-score envelopes whose statistical meaning shifts under heteroskedasticity and fat tails.",
                "url": "https://scholar.google.com/scholar?q=rolling+volatility+heteroskedasticity+technical+analysis",
            },
            {
                "title": "White (2000) - Reality Check",
                "summary": "Applies directly to BB parameter mining over period and standard-deviation multipliers.",
                "url": "https://scholar.google.com/scholar?q=White+2000+Reality+Check+for+Data+Snooping",
            },
            {
                "title": "Hansen (2005) - SPA",
                "summary": "Controls false positives when testing many BB breakout and mean-reversion variants.",
                "url": "https://scholar.google.com/scholar?q=Hansen+2005+Superior+Predictive+Ability",
            },
        ],
        "youtube_tutorials": [
            {
                "title": "Bollinger Bands and standard deviation tutorial",
                "focus": "Math-first interpretation of 20/2 setup and volatility regimes.",
                "url": "https://www.youtube.com/results?search_query=Bollinger+Bands+standard+deviation+tutorial",
            },
            {
                "title": "Bollinger Bands strategy guide",
                "focus": "Breakout vs mean-reversion setups and risk filters.",
                "url": "https://www.youtube.com/results?search_query=Bollinger+Bands+trading+strategy+tutorial",
            },
        ],
    },
    "stoch": {
        "research_stats": [
            "Cross-index tests find stochastic performance is strongly regime-dependent and often weaker than RSI or MACD without filtering.",
            "A high-frequency KDJ variant reported around 33.90% annual return and 2.24 Sharpe pre-cost in a best setting, but gains eroded after fees/slippage.",
            "ETF evidence shows stochastic can be competitive, with about 6.29% average annual return and top rank in about 45% of tested cases.",
        ],
        "research_papers": [
            {
                "title": "Oscillator Family Comparison Across Major Indices",
                "abstract": "Benchmarks stochastic against RSI, MACD, and PSAR net of commissions, showing substantial market-specific performance variance.",
                "key_stat": "Stochastic underperformed top oscillators in several index samples.",
                "url": "https://scholar.google.com/scholar?q=stochastic+oscillator+RSI+MACD+comparison+indices",
            },
            {
                "title": "Southeast Asian Indicator Study with Transaction Costs",
                "abstract": "Reports STOCH and STOCH-D results across five markets; some variants perform well but cost-adjusted edge remains inconsistent.",
                "key_stat": "STOCH-D often outperformed STOCH, yet profitability was fragile net of costs.",
                "url": "https://scholar.google.com/scholar?q=STOCH-D+technical+analysis+Southeast+Asia",
            },
            {
                "title": "ETF Indicator Backtest Comparison",
                "abstract": "Shows stochastic can rank near top on ETF universes under certain parameterizations and market phases.",
                "key_stat": "Average annual return around 6.29% versus about 6.01% buy-and-hold in the summary results.",
                "url": "https://scholar.google.com/scholar?q=ETF+stochastic+oscillator+performance+study",
            },
        ],
        "math_philosophy_papers": [
            {
                "title": "Range-Normalized Momentum Formulation",
                "summary": "Treats stochastic as close-location-value over rolling extrema; emphasizes noise sensitivity and smoothing trade-offs.",
                "url": "https://scholar.google.com/scholar?q=stochastic+oscillator+mathematical+formulation",
            },
            {
                "title": "White (2000) - Reality Check",
                "summary": "Directly relevant when scanning many stochastic windows and threshold combinations.",
                "url": "https://scholar.google.com/scholar?q=White+2000+Reality+Check+for+Data+Snooping",
            },
            {
                "title": "Bailey et al. (2014) - Backtest Overfitting",
                "summary": "Useful for evaluating how often selected stochastic settings are lucky rather than persistent.",
                "url": "https://scholar.google.com/scholar?q=Probability+of+Backtest+Overfitting+Bailey",
            },
        ],
        "youtube_tutorials": [
            {
                "title": "Stochastic oscillator concept tutorial",
                "focus": "Understand %K/%D crossings and overbought/oversold context.",
                "url": "https://www.youtube.com/results?search_query=stochastic+oscillator+tutorial",
            },
            {
                "title": "Stochastic oscillator practical setup",
                "focus": "Entry timing with trend filters and risk management.",
                "url": "https://www.youtube.com/results?search_query=how+to+use+stochastic+oscillator+trading",
            },
        ],
    },
    "adx": {
        "research_stats": [
            "ADX/DMI studies across regions show mixed raw profitability and frequent deterioration after trading costs.",
            "A long-horizon FX ADX plus PSAR system reported mixed pair-level outcomes, including a post-crisis Sharpe near 0.996 in one pair sample.",
            "An ML-driven DMI/ADMI study reported about 52.58% higher annual return than buy-and-hold and about 75.12% above traditional DMI in its tested universe.",
        ],
        "research_papers": [
            {
                "title": "DMI/ADX Rule Tests in Southeast Asian Equity Markets",
                "abstract": "Evaluates ADX-family trend filters across multiple markets and confirms strong dependence on market regime and cost assumptions.",
                "key_stat": "Shows profitability varies by market and frequently weakens net of costs.",
                "url": "https://scholar.google.com/scholar?q=DMI+ADX+Southeast+Asian+equity+markets",
            },
            {
                "title": "ADX + PSAR Weekly/Monthly FX Study (2000-2018)",
                "abstract": "Applies ADX-gated trend logic and PSAR trade management across major USD pairs; reports risk-adjusted metrics and crisis subperiod behavior.",
                "key_stat": "Reports mixed pair-level results, including one post-crisis Sharpe near 0.996.",
                "url": "https://scholar.google.com/scholar?q=ADX+PSAR+foreign+exchange+2000+2018",
            },
            {
                "title": "DMI-ADMI Signal Model with Recurrent Learning",
                "abstract": "Uses ADX-family signals as model inputs rather than fixed triggers and reports large relative improvements versus baseline DMI and buy-and-hold.",
                "key_stat": "Reported average annual return improvement: +52.58% vs buy-and-hold, +75.12% vs traditional DMI.",
                "url": "https://scholar.google.com/scholar?q=DMI+ADMI+recurrent+model+trading",
            },
        ],
        "math_philosophy_papers": [
            {
                "title": "Wilder (1978) Directional Movement System",
                "summary": "Defines +DI, -DI, and ADX smoothing mechanics and threshold interpretation.",
                "url": "https://scholar.google.com/scholar?q=New+Concepts+in+Technical+Trading+Systems+Wilder",
            },
            {
                "title": "Trend Strength as a Smoothed Ratio Process",
                "summary": "Interprets ADX as a non-directional strength estimator derived from directional movement normalized by true range.",
                "url": "https://scholar.google.com/scholar?q=average+directional+index+mathematical+analysis",
            },
            {
                "title": "Hansen (2005) - SPA",
                "summary": "Helpful for validating ADX threshold sweeps without overfitting conclusions.",
                "url": "https://scholar.google.com/scholar?q=Hansen+2005+Superior+Predictive+Ability",
            },
        ],
        "youtube_tutorials": [
            {
                "title": "ADX trend strength tutorial",
                "focus": "How to read ADX with +DI and -DI.",
                "url": "https://www.youtube.com/results?search_query=ADX+indicator+tutorial+DI",
            },
            {
                "title": "ADX filter for trend trading",
                "focus": "Using ADX thresholds to gate trend-following entries.",
                "url": "https://www.youtube.com/results?search_query=how+to+use+ADX+as+trend+filter",
            },
        ],
    },
    "ichimoku": {
        "research_stats": [
            "A Vietnam study reported mean ROI per transaction rising from about 0.0175 pre-pandemic to about 0.1036 during-pandemic, with p near 0.000028.",
            "Forecasting-oriented Ichimoku studies show stronger lagged-signal effects in some markets, but evidence is thinner than MA/RSI literature.",
            "Look-ahead mistakes are a major risk in Ichimoku backtests because Senkou spans are forward-shifted constructs.",
        ],
        "research_papers": [
            {
                "title": "Ichimoku Rule Profitability in Vietnam (Pre vs Pandemic)",
                "abstract": "Uses nonparametric tests plus bootstrap and Metropolis-Hastings robustness checks to compare Ichimoku transaction ROI distributions across regimes.",
                "key_stat": "Mean ROI per transaction: ~0.0175 pre-pandemic vs ~0.1036 during pandemic, p ~0.000028.",
                "url": "https://scholar.google.com/scholar?q=Ichimoku+Vietnam+pandemic+ROI+Mann+Whitney",
            },
            {
                "title": "Ichimoku Signals for Return Forecasting",
                "abstract": "Frames Ichimoku components as predictive features for next-period returns and evaluates statistical significance across developed markets.",
                "key_stat": "Reports strongest predictive effects in lagged signal specifications for selected markets.",
                "url": "https://scholar.google.com/scholar?q=Ichimoku+signals+returns+forecasting",
            },
            {
                "title": "Bibliometric and Methodological Survey of Ichimoku",
                "abstract": "Summarizes cloud mechanics, interpretation patterns, and evidence concentration by region and period.",
                "key_stat": "Highlights comparatively limited high-quality out-of-sample evidence versus mainstream indicators.",
                "url": "https://scholar.google.com/scholar?q=Ichimoku+bibliometric+analysis",
            },
        ],
        "math_philosophy_papers": [
            {
                "title": "Hosoda Framework and Midpoint Geometry",
                "summary": "Treats Ichimoku lines as rolling high-low midpoint geometry with temporal displacement, not as mystical support levels.",
                "url": "https://scholar.google.com/scholar?q=Ichimoku+mathematical+formulation+Hosoda",
            },
            {
                "title": "Look-Ahead Bias in Shifted Indicator Systems",
                "summary": "Explains why forward-shifted components must never be used as if they were known at decision time.",
                "url": "https://scholar.google.com/scholar?q=look-ahead+bias+technical+indicators+shifted",
            },
            {
                "title": "Bailey et al. (2014) - Backtest Overfitting",
                "summary": "Important because Ichimoku rule sets create large signal-combination search spaces.",
                "url": "https://scholar.google.com/scholar?q=Probability+of+Backtest+Overfitting+Bailey",
            },
        ],
        "youtube_tutorials": [
            {
                "title": "Complete Ichimoku cloud walkthrough",
                "focus": "Full system interpretation of Tenkan, Kijun, cloud, and Chikou.",
                "url": "https://www.youtube.com/results?search_query=Ichimoku+Cloud+full+tutorial",
            },
            {
                "title": "Ichimoku calculation and setup",
                "focus": "Formula-level understanding and backtesting cautions.",
                "url": "https://www.youtube.com/results?search_query=Ichimoku+Cloud+calculation+tutorial",
            },
        ],
    },
    "psar": {
        "research_stats": [
            "Cross-index oscillator tests often rank PSAR below RSI and MACD under cost-aware settings.",
            "PSAR performs best as trend-management logic paired with filters like ADX rather than as a standalone alpha signal.",
            "Range markets generate frequent stop-and-reverse churn, turning PSAR into a transaction-cost amplifier.",
        ],
        "research_papers": [
            {
                "title": "Cross-Index Oscillator Comparison Including PSAR",
                "abstract": "Evaluates PSAR net of commissions alongside RSI, MACD, and stochastic systems and finds large regime sensitivity.",
                "key_stat": "PSAR commonly underperformed stronger oscillators in tested index windows.",
                "url": "https://scholar.google.com/scholar?q=Parabolic+SAR+RSI+MACD+comparison+indices",
            },
            {
                "title": "ADX + PSAR FX Trading Evaluation",
                "abstract": "Combines ADX state filtering with PSAR trade management over long horizon FX samples, reporting mixed results across pairs.",
                "key_stat": "Supports PSAR as a management overlay, not reliable standalone entry engine.",
                "url": "https://scholar.google.com/scholar?q=ADX+Parabolic+SAR+foreign+exchange+study",
            },
            {
                "title": "PSAR Strategy Implementations in FX Contexts",
                "abstract": "Conference and practitioner-academic work evaluates PSAR rule mechanics in FX, generally emphasizing parameter sensitivity and trend dependence.",
                "key_stat": "Confirms high whipsaw exposure without external regime filters.",
                "url": "https://scholar.google.com/scholar?q=Parabolic+SAR+forex+strategy+evaluation",
            },
        ],
        "math_philosophy_papers": [
            {
                "title": "Wilder (1978) - PSAR Acceleration Framework",
                "summary": "Defines AF and EP mechanics that make PSAR a deterministic trailing stop path.",
                "url": "https://scholar.google.com/scholar?q=New+Concepts+in+Technical+Trading+Systems+Wilder",
            },
            {
                "title": "Trend-Following as Risk Control vs Alpha",
                "summary": "Separates PSAR's stop discipline value from true predictive signal claims.",
                "url": "https://scholar.google.com/scholar?q=trend+following+risk+control+vs+alpha",
            },
            {
                "title": "White (2000) - Reality Check",
                "summary": "Relevant when selecting AF step and max values through historical optimization.",
                "url": "https://scholar.google.com/scholar?q=White+2000+Reality+Check+for+Data+Snooping",
            },
        ],
        "youtube_tutorials": [
            {
                "title": "Parabolic SAR explained",
                "focus": "Understand SAR dots, trend flips, and trailing exits.",
                "url": "https://www.youtube.com/results?search_query=Parabolic+SAR+tutorial",
            },
            {
                "title": "PSAR strategy and stop management",
                "focus": "Practical entry/exit management with trend filters.",
                "url": "https://www.youtube.com/results?search_query=Parabolic+SAR+strategy+tutorial",
            },
        ],
    },
    "obv": {
        "research_stats": [
            "A dedicated Greater China OBV crossover study reported improving profitability using OBV moving-average windows such as 10, 20, 50, and 100.",
            "Multi-market studies find OBV can be significant in some markets, but many gains weaken materially after transaction costs.",
            "ETF-focused comparisons report mixed OBV outcomes, reinforcing that volume quality and market structure matter.",
        ],
        "research_papers": [
            {
                "title": "OBV Trading Rule Profitability in Greater China",
                "abstract": "Tests OBV versus OBV-moving-average crossovers and reports meaningful profitability trends across long horizon index samples.",
                "key_stat": "Evaluates 10/20/50/100 OBVMA windows and reports increasing profitability profile in sample.",
                "url": "https://scholar.google.com/scholar?q=On+Balance+Volume+Greater+China+trading+rule",
            },
            {
                "title": "Southeast Asian Indicator Study Including OBV",
                "abstract": "Compares indicator families across five markets and documents market-dependent OBV significance with substantial cost sensitivity.",
                "key_stat": "Some OBV signals are significant pre-cost, but robust net profitability is inconsistent.",
                "url": "https://scholar.google.com/scholar?q=OBV+technical+indicator+Southeast+Asian+markets",
            },
            {
                "title": "Technical Indicators on U.S. ETFs Including OBV",
                "abstract": "Tests indicator performance on ETF universes and shows OBV is sensitive to product choice and broader model context.",
                "key_stat": "OBV outcomes are mixed rather than uniformly superior.",
                "url": "https://scholar.google.com/scholar?q=OBV+ETF+technical+analysis+study",
            },
        ],
        "math_philosophy_papers": [
            {
                "title": "Granville Volume-Price Causality Thesis",
                "summary": "Philosophical basis of OBV: signed volume can lead price under accumulation/distribution dynamics.",
                "url": "https://scholar.google.com/scholar?q=Granville+On+Balance+Volume",
            },
            {
                "title": "Signed-Volume Transform and Information Content",
                "summary": "Treats OBV as a cumulative signed flow proxy and analyzes when volume may add incremental signal.",
                "url": "https://scholar.google.com/scholar?q=signed+volume+information+content+equity+markets",
            },
            {
                "title": "Sullivan, Timmermann, White (1999) Data-Snooping",
                "summary": "Important for OBVMA window selection where many candidate lengths are tested.",
                "url": "https://scholar.google.com/scholar?q=Sullivan+Timmermann+White+1999+data+snooping+technical+trading",
            },
        ],
        "youtube_tutorials": [
            {
                "title": "OBV beginner tutorial",
                "focus": "Accumulation-distribution reading with trend confirmation.",
                "url": "https://www.youtube.com/results?search_query=OBV+indicator+tutorial",
            },
            {
                "title": "OBV divergence strategy walkthrough",
                "focus": "Using OBV divergence and OBV moving average confirmation.",
                "url": "https://www.youtube.com/results?search_query=On+Balance+Volume+divergence+strategy",
            },
        ],
    },
}


def get_indicator_research_library() -> dict:
    return deepcopy(INDICATOR_RESEARCH_LIBRARY)
