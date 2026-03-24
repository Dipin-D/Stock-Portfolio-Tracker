from .golden_cross import GoldenCrossStrategy
from .momentum import MomentumStrategy


STRATEGY_REGISTRY = {
    GoldenCrossStrategy.slug: GoldenCrossStrategy,
    MomentumStrategy.slug: MomentumStrategy,
}


def get_strategy(slug: str):
    try:
        return STRATEGY_REGISTRY[slug]()
    except KeyError as error:
        raise ValueError(f"Unsupported strategy '{slug}'.") from error


def get_supported_strategies():
    return [strategy_class() for strategy_class in STRATEGY_REGISTRY.values()]

