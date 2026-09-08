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
    """TODO: implement this.

    Compare offer.claimed_in_stock against source.true_in_stock and return a
    Mismatch if they disagree. Write the test in tests/test_rules.py first.
    """
    raise NotImplementedError("check_stock is not implemented yet - see ROADMAP.md step 1")


def check_structured_attributes(offer: Offer, source: SourceRecord) -> list[Mismatch]:
    """TODO: implement this.

    For attributes in offer.claimed_attributes that have a directly comparable
    value in source.true_attributes (e.g. color, size, model number), compare
    them directly. Attributes that require interpreting free text (e.g.
    "gluten_free" against an ingredient list) don't belong here, that's
    src/llm_judge.py's job. Return a list because an offer can have multiple
    attribute mismatches at once.
    """
    raise NotImplementedError(
        "check_structured_attributes is not implemented yet - see ROADMAP.md step 2"
    )
