"""Deterministic verification rules.

Rules should be cheap and explainable: no API calls, no ambiguity. If a claim
needs interpretation (e.g. "is this description accurate"), it belongs in
src/llm_judge.py instead, not here.

Each rule function takes an Offer and its matching SourceRecord and returns
a Mismatch if it finds a problem, or None if the claim checks out.
"""

from src.schema import Mismatch, Offer, SourceRecord

PRICE_TOLERANCE = 0.02  # 2% - claimed price within this of true price is fine


def check_price(offer: Offer, source: SourceRecord) -> Mismatch | None:
    if source.true_price == 0:
        return None
    diff_ratio = abs(offer.claimed_price - source.true_price) / source.true_price
    if diff_ratio > PRICE_TOLERANCE:
        return Mismatch(
            field="price",
            claimed=offer.claimed_price,
            actual=source.true_price,
            detected_by="rule",
        )
    return None


def check_stock(offer: Offer, source: SourceRecord) -> Mismatch | None:
    if offer.claimed_in_stock == source.true_in_stock:
        return None

    return Mismatch(
        field="in_stock",
        claimed=offer.claimed_in_stock,
        actual=source.true_in_stock,
        detected_by="rule"
    )


def check_structured_attributes(offer: Offer, source: SourceRecord) -> list[Mismatch]:
    mismatches = []
    for key, claimed_value in offer.claimed_attributes.items():
        if key not in source.true_attributes:
            continue

        true_value = source.true_attributes[key]

        if claimed_value != true_value:
            mismatches.append(
                Mismatch(
                    field=f"attribute:{key}",
                    claimed=claimed_value,
                    actual=true_value,
                    detected_by="rule"
                )
            )

    return mismatches
