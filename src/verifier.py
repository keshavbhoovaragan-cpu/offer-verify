"""Orchestrates the rule tier and the LLM-judge tier into a single verdict
per offer.

Confidence thresholding (see README.md "Confidence threshold" for the full
writeup): a judge's is_match=False only counts as a real mismatch when its
confidence is at or above LLM_CONFIDENCE_THRESHOLD. Below that, the model
wasn't sure enough to trust either way, so the claim is left unverified
rather than flagged - a low-confidence "no" is not the same claim as a
high-confidence one, and treating them the same trades false negatives for
false positives without actually improving anything.
"""

from src import rules
from src.llm_judge import JudgeResult, LLMJudge
from src.schema import Mismatch, Offer, SourceRecord, VerificationVerdict

LLM_CONFIDENCE_THRESHOLD = 0.7


def verify_offer(offer: Offer, source: SourceRecord, judge: LLMJudge | None = None) -> VerificationVerdict:
    mismatches: list[Mismatch] = []

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

    # Attribute claims check_structured_attributes couldn't resolve (the key
    # isn't in source.true_attributes at all) get escalated to the LLM judge.
    judged: list[tuple[str, JudgeResult]] = []
    for key, claimed_value in offer.claimed_attributes.items():
        if key in source.true_attributes:
            continue  # already resolved by the rule tier

        if judge is None:
            judge = LLMJudge()
        result = judge.judge_attribute_claim(offer, source, key)
        judged.append((key, result))

        if result.confidence < LLM_CONFIDENCE_THRESHOLD:
            continue  # unverifiable - not confident enough to call it either way
        if not result.is_match:
            mismatches.append(
                Mismatch(
                    field=f"attribute:{key}",
                    claimed=claimed_value,
                    actual=result.rationale,
                    detected_by="llm",
                )
            )

    is_verified = len(mismatches) == 0
    rule_mismatches = [m for m in mismatches if m.detected_by == "rule"]
    llm_mismatches = [m for m in mismatches if m.detected_by == "llm"]

    if rule_mismatches:
        # Rules are exact/deterministic - a rule-caught mismatch is certain.
        confidence = 1.0
    elif llm_mismatches:
        # Confidence in the verdict is only as strong as the weakest judged
        # mismatch that tripped it.
        confidence = min(
            result.confidence for _, result in judged if not result.is_match and result.confidence >= LLM_CONFIDENCE_THRESHOLD
        )
    elif judged:
        # Verified, but partly on the strength of the judge's matching
        # confidence rather than a deterministic rule.
        confidence = sum(result.confidence for _, result in judged) / len(judged)
    else:
        confidence = 1.0

    method = "rule+llm" if judged else "rule"

    return VerificationVerdict(
        offer_id=offer.offer_id,
        is_verified=is_verified,
        mismatches=mismatches,
        confidence=confidence,
        method=method,
        judged_attributes=judged,
    )


def verify_all(offers: list[Offer], source_by_key: dict[str, SourceRecord]) -> list[VerificationVerdict]:
    judge = LLMJudge()
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
        verdicts.append(verify_offer(offer, source, judge=judge))
    return verdicts
