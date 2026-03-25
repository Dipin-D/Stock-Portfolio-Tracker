from .golden_cross import GoldenCrossStrategy
from .golden_cross_bollinger import (
    GoldenCrossBollingerBreakoutConfirmStrategy,
    GoldenCrossBollingerSqueezeStrategy,
)
from .momentum import MomentumStrategy


STRATEGY_REGISTRY = {
    GoldenCrossStrategy.slug: GoldenCrossStrategy,
    GoldenCrossBollingerSqueezeStrategy.slug: GoldenCrossBollingerSqueezeStrategy,
    GoldenCrossBollingerBreakoutConfirmStrategy.slug: GoldenCrossBollingerBreakoutConfirmStrategy,
    MomentumStrategy.slug: MomentumStrategy,
}


def get_strategy(slug: str):
    try:
        return STRATEGY_REGISTRY[slug]()
    except KeyError as error:
        raise ValueError(f"Unsupported strategy '{slug}'.") from error


def get_supported_strategies():
    return [strategy_class() for strategy_class in STRATEGY_REGISTRY.values()]
