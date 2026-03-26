from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Iterable

from .indicator_library import get_indicator_library


DOMAIN_TAXONOMY = [
    {
        "slug": "markets",
        "name": "Markets",
        "summary": "Benchmarks, structure, liquidity, and broad market behavior.",
        "description": "Understand benchmark indices, liquidity cycles, and the market structure that shapes how prices move.",
        "related": ["economic-terms", "sectors", "technical-analysis"],
    },
    {
        "slug": "strategies",
        "name": "Strategies",
        "summary": "Playbooks used to convert market context into trade ideas.",
        "description": "Learn practical strategy frameworks, when they work, and what market context each setup needs.",
        "related": ["risk-management", "trading-psychology", "indicators"],
    },
    {
        "slug": "indicators",
        "name": "Indicators",
        "summary": "Momentum, trend, volatility, and volume studies.",
        "description": "Understand the tools traders use to measure momentum, trend, volatility, and volume.",
        "related": ["technical-analysis", "strategies", "risk-management"],
    },
    {
        "slug": "sectors",
        "name": "Sectors",
        "summary": "How industry groups rotate through market cycles.",
        "description": "Track cyclical and defensive sector behavior, relative strength, and rotation context.",
        "related": ["markets", "companies", "economic-terms"],
    },
    {
        "slug": "companies",
        "name": "Companies",
        "summary": "Business-level concepts for equity analysis.",
        "description": "Review company-level metrics and operational concepts used in equity research.",
        "related": ["fundamental-analysis", "sectors", "markets"],
    },
    {
        "slug": "economic-terms",
        "name": "Economic Terms",
        "summary": "Macro concepts that affect rates, inflation, and sentiment.",
        "description": "Decode macro vocabulary that drives monetary policy expectations and risk appetite.",
        "related": ["markets", "sectors", "risk-management"],
    },
    {
        "slug": "risk-management",
        "name": "Risk Management",
        "summary": "Position sizing, drawdown control, and exposure discipline.",
        "description": "Manage downside first with sizing rules, risk budgeting, and portfolio-level protection tactics.",
        "related": ["strategies", "trading-psychology", "technical-analysis"],
    },
    {
        "slug": "technical-analysis",
        "name": "Technical Analysis",
        "summary": "Price action, patterns, and chart-based signal interpretation.",
        "description": "Read trend structure, support and resistance, and pattern context directly from price action.",
        "related": ["indicators", "strategies", "markets"],
    },
    {
        "slug": "fundamental-analysis",
        "name": "Fundamental Analysis",
        "summary": "Valuation, profitability, growth, and capital efficiency.",
        "description": "Evaluate valuation and operating quality through the core financial metrics used by investors.",
        "related": ["companies", "markets", "economic-terms"],
    },
    {
        "slug": "trading-psychology",
        "name": "Trading Psychology",
        "summary": "Decision quality, discipline, and behavioral bias control.",
        "description": "Improve consistency by recognizing emotional bias, process breakdowns, and execution drift.",
        "related": ["risk-management", "strategies", "technical-analysis"],
    },
]


DIFFICULTY_ORDER = {
    "Beginner": 0,
    "Intermediate": 1,
    "Advanced": 2,
}


SORT_OPTIONS = [
    {"value": "updated", "label": "Recently updated"},
    {"value": "az", "label": "A-Z"},
    {"value": "views", "label": "Most viewed"},
]


def _entry(
    *,
    slug: str,
    title: str,
    summary: str,
    domain_slug: str,
    subcategory: str,
    difficulty: str,
    content_type: str,
    read_time: str,
    last_updated: str,
    tags: Iterable[str],
    views: int,
    featured: bool = False,
) -> dict:
    return {
        "slug": slug,
        "title": title,
        "summary": summary,
        "domain_slug": domain_slug,
        "subcategory": subcategory,
        "difficulty": difficulty,
        "content_type": content_type,
        "read_time": read_time,
        "last_updated": date.fromisoformat(last_updated),
        "tags": [str(tag) for tag in tags],
        "views": int(views),
        "featured": bool(featured),
    }


BASE_ARTICLE_CATALOG = [
    _entry(
        slug="sp-500",
        title="S&P 500",
        summary="A large-cap U.S. equity benchmark used as a baseline for market performance and risk sentiment.",
        domain_slug="markets",
        subcategory="Benchmarks",
        difficulty="Beginner",
        content_type="Concept",
        read_time="5 min",
        last_updated="2026-03-22",
        tags=["index", "benchmark", "equities"],
        views=2985,
        featured=True,
    ),
    _entry(
        slug="market-breadth",
        title="Market Breadth",
        summary="Measures how many stocks participate in a move, helping separate broad trends from narrow rallies.",
        domain_slug="markets",
        subcategory="Structure",
        difficulty="Intermediate",
        content_type="Concept",
        read_time="6 min",
        last_updated="2026-03-19",
        tags=["advance-decline", "participation", "trend quality"],
        views=1560,
    ),
    _entry(
        slug="market-liquidity",
        title="Market Liquidity",
        summary="The ease of entering and exiting positions without large price impact during normal trading conditions.",
        domain_slug="markets",
        subcategory="Microstructure",
        difficulty="Intermediate",
        content_type="Concept",
        read_time="7 min",
        last_updated="2026-03-16",
        tags=["spread", "depth", "execution"],
        views=1210,
    ),
    _entry(
        slug="trend-following",
        title="Trend Following",
        summary="A strategy family that aligns entries and exits with persistent directional price movement.",
        domain_slug="strategies",
        subcategory="Trend",
        difficulty="Beginner",
        content_type="Playbook",
        read_time="7 min",
        last_updated="2026-03-20",
        tags=["momentum", "position management", "trend"],
        views=2140,
    ),
    _entry(
        slug="mean-reversion",
        title="Mean Reversion",
        summary="A strategy style that looks for stretched prices to normalize back toward a historical average.",
        domain_slug="strategies",
        subcategory="Reversion",
        difficulty="Intermediate",
        content_type="Playbook",
        read_time="8 min",
        last_updated="2026-03-15",
        tags=["oversold", "overbought", "range behavior"],
        views=1715,
    ),
    _entry(
        slug="breakout-trading",
        title="Breakout Trading",
        summary="Targets expansion moves when price exits a consolidation range with confirmation.",
        domain_slug="strategies",
        subcategory="Breakout",
        difficulty="Intermediate",
        content_type="Playbook",
        read_time="8 min",
        last_updated="2026-03-11",
        tags=["volatility expansion", "range", "entry timing"],
        views=1890,
    ),
    _entry(
        slug="swing-trading",
        title="Swing Trading",
        summary="Captures multi-day to multi-week moves by balancing trend context with tactical entries.",
        domain_slug="strategies",
        subcategory="Execution",
        difficulty="Beginner",
        content_type="Playbook",
        read_time="6 min",
        last_updated="2026-03-13",
        tags=["holding period", "risk control", "timing"],
        views=1650,
    ),
    _entry(
        slug="sector-rotation",
        title="Sector Rotation",
        summary="Tracks leadership shifts between sector groups as economic and policy expectations change.",
        domain_slug="sectors",
        subcategory="Rotation",
        difficulty="Intermediate",
        content_type="Concept",
        read_time="7 min",
        last_updated="2026-03-14",
        tags=["relative strength", "macro cycle", "allocation"],
        views=1180,
    ),
    _entry(
        slug="defensive-vs-cyclical-sectors",
        title="Defensive vs Cyclical Sectors",
        summary="Compares resilient sectors with growth-sensitive sectors to read changing market appetite.",
        domain_slug="sectors",
        subcategory="Classification",
        difficulty="Beginner",
        content_type="Concept",
        read_time="5 min",
        last_updated="2026-03-09",
        tags=["utilities", "consumer staples", "industrials"],
        views=980,
    ),
    _entry(
        slug="market-capitalization",
        title="Market Capitalization",
        summary="Company size metric used to classify stocks and benchmark style exposure.",
        domain_slug="companies",
        subcategory="Classification",
        difficulty="Beginner",
        content_type="Glossary",
        read_time="4 min",
        last_updated="2026-03-18",
        tags=["large cap", "mid cap", "small cap"],
        views=1425,
    ),
    _entry(
        slug="free-cash-flow",
        title="Free Cash Flow",
        summary="Cash generated after operating and capital expenses, often used to evaluate financial durability.",
        domain_slug="companies",
        subcategory="Cash Flow",
        difficulty="Intermediate",
        content_type="Metric",
        read_time="6 min",
        last_updated="2026-03-17",
        tags=["cash generation", "capex", "valuation"],
        views=1340,
    ),
    _entry(
        slug="consumer-price-index-cpi",
        title="Consumer Price Index (CPI)",
        summary="A core inflation metric that influences rate expectations and equity valuation multiples.",
        domain_slug="economic-terms",
        subcategory="Inflation",
        difficulty="Beginner",
        content_type="Glossary",
        read_time="5 min",
        last_updated="2026-03-12",
        tags=["inflation", "macro", "policy"],
        views=1725,
    ),
    _entry(
        slug="federal-funds-rate",
        title="Federal Funds Rate",
        summary="Policy rate target set by the Federal Reserve that shapes borrowing costs across markets.",
        domain_slug="economic-terms",
        subcategory="Rates",
        difficulty="Beginner",
        content_type="Glossary",
        read_time="5 min",
        last_updated="2026-03-21",
        tags=["fed", "rates", "macro"],
        views=1885,
    ),
    _entry(
        slug="risk-reward-ratio",
        title="Risk/Reward Ratio",
        summary="Compares potential upside to downside per trade and anchors position-level decision quality.",
        domain_slug="risk-management",
        subcategory="Trade Risk",
        difficulty="Beginner",
        content_type="Framework",
        read_time="5 min",
        last_updated="2026-03-23",
        tags=["stop loss", "target", "expectancy"],
        views=2460,
        featured=True,
    ),
    _entry(
        slug="position-sizing",
        title="Position Sizing",
        summary="Determines how much capital to allocate per trade so one loss does not damage portfolio survival.",
        domain_slug="risk-management",
        subcategory="Portfolio Risk",
        difficulty="Intermediate",
        content_type="Framework",
        read_time="7 min",
        last_updated="2026-03-20",
        tags=["risk budget", "sizing", "volatility"],
        views=2210,
    ),
    _entry(
        slug="maximum-drawdown",
        title="Maximum Drawdown",
        summary="Measures the worst peak-to-trough decline in equity curve terms for strategy risk evaluation.",
        domain_slug="risk-management",
        subcategory="Portfolio Risk",
        difficulty="Intermediate",
        content_type="Metric",
        read_time="6 min",
        last_updated="2026-03-18",
        tags=["equity curve", "risk", "capital preservation"],
        views=1325,
    ),
    _entry(
        slug="support-and-resistance",
        title="Support and Resistance",
        summary="Chart levels where supply and demand repeatedly react, often shaping entry and stop placement.",
        domain_slug="technical-analysis",
        subcategory="Structure",
        difficulty="Beginner",
        content_type="Pattern Guide",
        read_time="6 min",
        last_updated="2026-03-19",
        tags=["price levels", "breakout", "retest"],
        views=2055,
    ),
    _entry(
        slug="head-and-shoulders",
        title="Head and Shoulders",
        summary="A reversal pattern that can flag trend fatigue when confirmed by neckline breakdown.",
        domain_slug="technical-analysis",
        subcategory="Chart Patterns",
        difficulty="Intermediate",
        content_type="Pattern Guide",
        read_time="7 min",
        last_updated="2026-03-10",
        tags=["reversal", "pattern", "neckline"],
        views=1205,
    ),
    _entry(
        slug="candlestick-confirmation",
        title="Candlestick Confirmation",
        summary="Uses candle structure to validate or reject broader setup context before execution.",
        domain_slug="technical-analysis",
        subcategory="Price Action",
        difficulty="Beginner",
        content_type="Pattern Guide",
        read_time="5 min",
        last_updated="2026-03-08",
        tags=["candle patterns", "entry timing", "rejection"],
        views=1090,
    ),
    _entry(
        slug="earnings-per-share",
        title="Earnings Per Share (EPS)",
        summary="A profitability metric that shows how much net income is attributable per outstanding share.",
        domain_slug="fundamental-analysis",
        subcategory="Profitability",
        difficulty="Beginner",
        content_type="Metric",
        read_time="5 min",
        last_updated="2026-03-24",
        tags=["income statement", "valuation", "quality"],
        views=2640,
        featured=True,
    ),
    _entry(
        slug="price-to-earnings-ratio",
        title="Price-to-Earnings Ratio (P/E)",
        summary="Valuation ratio comparing stock price to earnings, often used relative to growth and peers.",
        domain_slug="fundamental-analysis",
        subcategory="Valuation",
        difficulty="Beginner",
        content_type="Metric",
        read_time="6 min",
        last_updated="2026-03-21",
        tags=["valuation", "multiples", "fundamentals"],
        views=2130,
    ),
    _entry(
        slug="return-on-equity",
        title="Return on Equity (ROE)",
        summary="Measures how effectively a company converts shareholder equity into net profit.",
        domain_slug="fundamental-analysis",
        subcategory="Capital Efficiency",
        difficulty="Intermediate",
        content_type="Metric",
        read_time="6 min",
        last_updated="2026-03-16",
        tags=["profitability", "efficiency", "quality"],
        views=1185,
    ),
    _entry(
        slug="fomo-in-trading",
        title="FOMO in Trading",
        summary="Fear of missing out can trigger poor entries, oversized positions, and plan violations.",
        domain_slug="trading-psychology",
        subcategory="Behavioral Biases",
        difficulty="Beginner",
        content_type="Behavior Guide",
        read_time="5 min",
        last_updated="2026-03-14",
        tags=["discipline", "emotion", "execution"],
        views=1470,
    ),
    _entry(
        slug="loss-aversion",
        title="Loss Aversion",
        summary="The tendency to hold losers too long and cut winners too early due to emotional discomfort.",
        domain_slug="trading-psychology",
        subcategory="Behavioral Biases",
        difficulty="Intermediate",
        content_type="Behavior Guide",
        read_time="6 min",
        last_updated="2026-03-12",
        tags=["bias", "risk", "process"],
        views=990,
    ),
    _entry(
        slug="trading-journal",
        title="Trading Journal",
        summary="A structured review process that improves decision quality through repeatable post-trade feedback.",
        domain_slug="trading-psychology",
        subcategory="Process Discipline",
        difficulty="Beginner",
        content_type="Behavior Guide",
        read_time="6 min",
        last_updated="2026-03-17",
        tags=["review", "process", "improvement"],
        views=1380,
    ),
]


INDICATOR_META = {
    "ma": {
        "slug": "moving-average",
        "subcategory": "Trend",
        "difficulty": "Beginner",
        "content_type": "Indicator Guide",
        "read_time": "7 min",
        "last_updated": "2026-03-24",
        "views": 3275,
        "featured": True,
    },
    "rsi": {
        "slug": "relative-strength-index-rsi",
        "subcategory": "Momentum",
        "difficulty": "Beginner",
        "content_type": "Indicator Guide",
        "read_time": "7 min",
        "last_updated": "2026-03-25",
        "views": 3540,
        "featured": True,
    },
    "bbands": {
        "slug": "bollinger-bands",
        "subcategory": "Volatility",
        "difficulty": "Intermediate",
        "content_type": "Indicator Guide",
        "read_time": "8 min",
        "last_updated": "2026-03-22",
        "views": 2920,
        "featured": False,
    },
    "stoch": {
        "slug": "stochastic-oscillator",
        "subcategory": "Momentum",
        "difficulty": "Intermediate",
        "content_type": "Indicator Guide",
        "read_time": "7 min",
        "last_updated": "2026-03-18",
        "views": 1870,
        "featured": False,
    },
    "adx": {
        "slug": "average-directional-index-adx",
        "subcategory": "Trend",
        "difficulty": "Intermediate",
        "content_type": "Indicator Guide",
        "read_time": "7 min",
        "last_updated": "2026-03-20",
        "views": 1760,
        "featured": False,
    },
    "ichimoku": {
        "slug": "ichimoku-cloud",
        "subcategory": "Trend",
        "difficulty": "Advanced",
        "content_type": "Indicator Guide",
        "read_time": "10 min",
        "last_updated": "2026-03-17",
        "views": 1555,
        "featured": False,
    },
    "psar": {
        "slug": "parabolic-sar",
        "subcategory": "Trend",
        "difficulty": "Intermediate",
        "content_type": "Indicator Guide",
        "read_time": "7 min",
        "last_updated": "2026-03-15",
        "views": 1285,
        "featured": False,
    },
    "obv": {
        "slug": "on-balance-volume-obv",
        "subcategory": "Volume",
        "difficulty": "Intermediate",
        "content_type": "Indicator Guide",
        "read_time": "6 min",
        "last_updated": "2026-03-19",
        "views": 1495,
        "featured": False,
    },
}


def _build_indicator_entries() -> list[dict]:
    entries = []
    for indicator in get_indicator_library():
        slug = str(indicator.get("slug") or "").strip()
        meta = INDICATOR_META.get(slug)
        if not meta:
            continue

        entries.append(
            _entry(
                slug=meta["slug"],
                title=indicator.get("name", "").strip(),
                summary=indicator.get("preview", "").strip(),
                domain_slug="indicators",
                subcategory=meta["subcategory"],
                difficulty=meta["difficulty"],
                content_type=meta["content_type"],
                read_time=meta["read_time"],
                last_updated=meta["last_updated"],
                tags=[indicator.get("short_name", "").strip(), meta["subcategory"], "indicator"],
                views=meta["views"],
                featured=meta["featured"],
            )
        )
    return entries


ARTICLE_CATALOG = [*BASE_ARTICLE_CATALOG, *_build_indicator_entries()]

DOMAIN_MAP = {domain["slug"]: dict(domain) for domain in DOMAIN_TAXONOMY}
ARTICLE_MAP = {article["slug"]: dict(article) for article in ARTICLE_CATALOG}
FEATURED_TOPIC_SLUGS = [
    "relative-strength-index-rsi",
    "moving-average",
    "sp-500",
    "earnings-per-share",
    "risk-reward-ratio",
]


HOMEPAGE_CATEGORY_CARDS = [
    {
        "slug": "indicators",
        "title": "Indicators",
        "summary": "Signal studies for trend, momentum, volatility, and volume behavior.",
        "icon": "IND",
        "domain_slugs": ["indicators"],
    },
    {
        "slug": "strategies",
        "title": "Strategies",
        "summary": "Execution playbooks for trend, breakout, and mean-reversion setups.",
        "icon": "STR",
        "domain_slugs": ["strategies"],
    },
    {
        "slug": "market-concepts",
        "title": "Market Concepts",
        "summary": "Foundational terms covering benchmarks, structure, and macro context.",
        "icon": "MKT",
        "domain_slugs": ["markets", "economic-terms", "sectors"],
    },
    {
        "slug": "company-metrics",
        "title": "Company Metrics",
        "summary": "Fundamental metrics used to evaluate valuation and business quality.",
        "icon": "MET",
        "domain_slugs": ["companies", "fundamental-analysis"],
    },
    {
        "slug": "chart-patterns",
        "title": "Chart Patterns",
        "summary": "Structure, price action, and recurring formations used in execution.",
        "icon": "PAT",
        "domain_slugs": ["technical-analysis"],
    },
    {
        "slug": "risk-management",
        "title": "Risk Management",
        "summary": "Frameworks for sizing, drawdown control, and exposure discipline.",
        "icon": "RSK",
        "domain_slugs": ["risk-management"],
    },
]


HOMEPAGE_CATEGORY_TARGETS = {
    "indicators": "/encyclopedia/indicators/",
    "strategies": "/encyclopedia/strategies/",
    "market-concepts": "/encyclopedia/markets/",
    "company-metrics": "/encyclopedia/fundamental-analysis/",
    "chart-patterns": "/encyclopedia/technical-analysis/",
    "risk-management": "/encyclopedia/risk-management/",
}


def _domain_counts() -> Counter:
    return Counter(article["domain_slug"] for article in ARTICLE_CATALOG)


def _article_url(article: dict) -> str:
    return f"/encyclopedia/{article['domain_slug']}/#{article['slug']}"


def _clone_article(article: dict, domain_name: str) -> dict:
    payload = dict(article)
    payload["domain_name"] = domain_name
    payload["url"] = _article_url(article)
    payload["tags"] = list(article.get("tags", []))
    return payload


def _domain_payloads() -> list[dict]:
    counts = _domain_counts()
    payloads = []
    for domain in DOMAIN_TAXONOMY:
        item = dict(domain)
        item["article_count"] = int(counts.get(domain["slug"], 0))
        payloads.append(item)
    return payloads


def _all_articles() -> list[dict]:
    items = []
    for article in ARTICLE_CATALOG:
        domain = DOMAIN_MAP.get(article["domain_slug"], {})
        items.append(_clone_article(article, domain.get("name", "")))
    return items


def _search_articles(articles: list[dict], query: str) -> list[dict]:
    normalized = str(query or "").strip().lower()
    if not normalized:
        return []

    def score(item: dict) -> int:
        title = item["title"].lower()
        summary = item["summary"].lower()
        tags_blob = " ".join(item.get("tags", [])).lower()
        subcategory = item.get("subcategory", "").lower()
        domain = item.get("domain_name", "").lower()

        total = 0
        if normalized in title:
            total += 5
        if normalized in tags_blob:
            total += 3
        if normalized in subcategory:
            total += 2
        if normalized in domain:
            total += 2
        if normalized in summary:
            total += 1
        return total

    matched = [item for item in articles if score(item) > 0]
    matched.sort(key=lambda item: (score(item), item["views"], item["last_updated"]), reverse=True)
    return matched


def get_encyclopedia_home_context(search_query: str = "") -> dict:
    all_articles = _all_articles()
    article_by_slug = {article["slug"]: article for article in all_articles}

    featured_topics = [article_by_slug[slug] for slug in FEATURED_TOPIC_SLUGS if slug in article_by_slug]
    recently_updated = sorted(all_articles, key=lambda item: item["last_updated"], reverse=True)[:6]
    popular_in_search = sorted(all_articles, key=lambda item: item["views"], reverse=True)[:8]
    domain_payloads = _domain_payloads()

    category_cards = []
    for card in HOMEPAGE_CATEGORY_CARDS:
        payload = dict(card)
        payload["article_count"] = sum(
            1 for article in all_articles if article["domain_slug"] in card["domain_slugs"]
        )
        payload["url"] = HOMEPAGE_CATEGORY_TARGETS.get(card["slug"], "/encyclopedia/")
        category_cards.append(payload)

    normalized_query = str(search_query or "").strip()
    search_results = _search_articles(all_articles, normalized_query)[:8] if normalized_query else []
    az_index = sorted({article["title"][0].upper() for article in all_articles if article["title"]})

    return {
        "total_article_count": len(all_articles),
        "taxonomy_domains": domain_payloads,
        "featured_topics": featured_topics,
        "category_cards": category_cards,
        "recently_updated": recently_updated,
        "popular_in_search": popular_in_search,
        "search_query": normalized_query,
        "search_results": search_results,
        "az_index": az_index,
    }


def get_encyclopedia_category_context(
    category_slug: str,
    *,
    search_query: str = "",
    subcategory: str = "all",
    difficulty: str = "all",
    content_type: str = "all",
    sort: str = "updated",
) -> dict | None:
    domain = DOMAIN_MAP.get(str(category_slug or "").strip())
    if domain is None:
        return None

    domain_articles = [
        _clone_article(article, domain["name"])
        for article in ARTICLE_CATALOG
        if article["domain_slug"] == domain["slug"]
    ]

    subcategory_options = sorted({article["subcategory"] for article in domain_articles})
    difficulty_options = [
        level for level in ("Beginner", "Intermediate", "Advanced")
        if any(article["difficulty"] == level for article in domain_articles)
    ]
    content_type_options = sorted({article["content_type"] for article in domain_articles})

    normalized_search = str(search_query or "").strip().lower()
    normalized_subcategory = str(subcategory or "all").strip()
    normalized_difficulty = str(difficulty or "all").strip()
    normalized_content_type = str(content_type or "all").strip()
    normalized_sort = sort if any(sort == option["value"] for option in SORT_OPTIONS) else "updated"

    filtered = []
    for article in domain_articles:
        if normalized_search:
            haystack = " ".join(
                [
                    article["title"],
                    article["summary"],
                    article["subcategory"],
                    article["content_type"],
                    " ".join(article.get("tags", [])),
                ]
            ).lower()
            if normalized_search not in haystack:
                continue

        if normalized_subcategory != "all" and article["subcategory"] != normalized_subcategory:
            continue
        if normalized_difficulty != "all" and article["difficulty"] != normalized_difficulty:
            continue
        if normalized_content_type != "all" and article["content_type"] != normalized_content_type:
            continue

        filtered.append(article)

    if normalized_sort == "az":
        filtered.sort(key=lambda item: item["title"].lower())
    elif normalized_sort == "views":
        filtered.sort(key=lambda item: (item["views"], item["last_updated"]), reverse=True)
    else:
        filtered.sort(key=lambda item: item["last_updated"], reverse=True)

    featured_articles = [item for item in domain_articles if item.get("featured")]
    if not featured_articles:
        featured_articles = sorted(domain_articles, key=lambda item: item["views"], reverse=True)[:4]
    else:
        featured_articles = sorted(
            featured_articles,
            key=lambda item: (item["views"], item["last_updated"]),
            reverse=True,
        )[:4]

    related_categories = []
    counts = _domain_counts()
    for related_slug in domain.get("related", []):
        related_domain = DOMAIN_MAP.get(related_slug)
        if not related_domain:
            continue
        related_categories.append(
            {
                "slug": related_slug,
                "name": related_domain["name"],
                "summary": related_domain["summary"],
                "article_count": int(counts.get(related_slug, 0)),
                "url": f"/encyclopedia/{related_slug}/",
            }
        )

    beginner_starting_points = [
        article for article in sorted(domain_articles, key=lambda item: item["views"], reverse=True)
        if article["difficulty"] == "Beginner"
    ][:4]

    recent_articles = sorted(domain_articles, key=lambda item: item["last_updated"], reverse=True)[:4]

    return {
        "category": {
            "slug": domain["slug"],
            "name": domain["name"],
            "summary": domain["summary"],
            "description": domain["description"],
            "article_count": len(domain_articles),
        },
        "articles": filtered,
        "total_article_count": len(domain_articles),
        "filtered_article_count": len(filtered),
        "featured_articles": featured_articles,
        "related_categories": related_categories,
        "beginner_starting_points": beginner_starting_points,
        "recent_articles": recent_articles,
        "filter_state": {
            "search_query": str(search_query or "").strip(),
            "subcategory": normalized_subcategory if normalized_subcategory in subcategory_options else "all",
            "difficulty": normalized_difficulty if normalized_difficulty in difficulty_options else "all",
            "content_type": normalized_content_type if normalized_content_type in content_type_options else "all",
            "sort": normalized_sort,
        },
        "subcategory_options": subcategory_options,
        "difficulty_options": sorted(
            difficulty_options,
            key=lambda level: DIFFICULTY_ORDER.get(level, 99),
        ),
        "content_type_options": content_type_options,
        "sort_options": SORT_OPTIONS,
    }
