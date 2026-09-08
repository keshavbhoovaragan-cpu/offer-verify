"""Orchestrates the rule tier (and eventually the LLM-judge tier) into a
single verdict per offer.

Design note: rules that aren't implemented yet raise NotImplementedError.
verify_offer() catches that and just skips the check, so the pipeline stays
runnable end to end as you build out src/rules.py and src/llm_judge.py one
piece at a time. Remove that try/except once everything's implemented, it's
a scaffolding aid, not a permanent design choice.
"""

from src import rules
from src.schema import Offer, SourceRecord, VerificationVerdict


def verify_offer(offer: Offer, source: SourceRecord) -> VerificationVerdict:
    mismatches = []

    price_mismatch = rules.check_price(offer, source)
    if price_mismatch:
        mismatches.append(price_mismatch)

    for check in (rules.check_stock, rules.check_structured_attributes):
        try:
            result = check(offer, source)
        except NotImplementedError:
            continue
        if result:
            if isinstance(result, list):
                mismatches.extend(result)
            else:
                mismatches.append(result)

    # TODO (ROADMAP.md step 4-5): escalate unresolved unstructured attribute
    # claims to LLMJudge here, fold its results into `mismatches`, and use
    # its confidence to inform the verdict's overall confidence below instead
    # of the flat 1.0 / 0.6 placeholder.

    is_verified = len(mismatches) == 0
    confidence = 1.0 if is_verified else 0.6

    return VerificationVerdict(
        offer_id=offer.offer_id,
        is_verified=is_verified,
        mismatches=mismatches,
        confidence=confidence,
        method="rule",
    )


def verify_all(offers: list[Offer], source_by_key: dict[str, SourceRecord]) -> list[VerificationVerdict]:
    verdicts = []
    for offer in offers:
        source = source_by_key.get(offer.product_key)
        if source is None:
            verdicts.append(
                VerificationVerdict(
                    offer_id=offer.offer_id,
                    is_verified=False,
                    mismatches=[],
                    confidence=0.0,
                    method="no_source_match",
                )
            )
            continue
        verdicts.append(verify_offer(offer, source))
    return verdicts
