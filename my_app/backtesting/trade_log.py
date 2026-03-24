from __future__ import annotations


def serialize_trade(trade: dict, sequence_index: int) -> dict:
    serialized = dict(trade)
    serialized["sequence_index"] = sequence_index
    return serialized

