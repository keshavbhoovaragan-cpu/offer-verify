"""Load offers and source records from JSON and join them by product_key."""

import json
from pathlib import Path

from src.schema import Offer, SourceRecord


def load_offers(path: str | Path) -> list[Offer]:
    with open(path) as f:
        raw = json.load(f)
    return [Offer(**item) for item in raw]


def load_source_feed(path: str | Path) -> dict[str, SourceRecord]:
    """Returns a dict keyed by product_key for O(1) lookup during verification."""
    with open(path) as f:
        raw = json.load(f)
    records = [SourceRecord(**item) for item in raw]
    return {r.product_key: r for r in records}


def load_labeled_mismatches(path: str | Path) -> set[str]:
    """Returns the set of offer_ids that are known (hand-labeled) mismatches,
    used by src/metrics.py to score the pipeline's precision/recall."""
    with open(path) as f:
        raw = json.load(f)
    return set(raw["mismatched_offer_ids"])
