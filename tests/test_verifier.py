"""Tests for verify_offer's LLM-tier wiring and confidence thresholding,
using a stub judge so these run offline without an API key.
"""

from src.llm_judge import JudgeResult
from src.schema import Offer, SourceRecord
from src.verifier import LLM_CONFIDENCE_THRESHOLD, verify_offer


def make_offer(**overrides):
    base = dict(
        offer_id="o1",
        merchant_id="m1",
        product_key="p1",
        product_title="Test product",
        claimed_price=10.0,
        claimed_in_stock=True,
        claimed_attributes={"vegan": True},
    )
    base.update(overrides)
    return Offer(**base)


def make_source(**overrides):
    base = dict(
        product_key="p1",
        merchant_id="m1",
        canonical_title="Test product",
        true_price=10.0,
        true_in_stock=True,
        true_attributes={},
        evidence_text="Ingredients: whey protein isolate.",
    )
    base.update(overrides)
    return SourceRecord(**base)


class StubJudge:
    def __init__(self, result: JudgeResult):
        self.result = result
        self.calls = []

    def judge_attribute_claim(self, offer, source, attribute):
        self.calls.append((offer.offer_id, attribute))
        return self.result


def test_structured_attribute_is_never_escalated_to_llm():
    judge = StubJudge(JudgeResult(is_match=True, confidence=0.99, rationale="unused"))
    offer = make_offer(claimed_attributes={"color": "black"})
    source = make_source(true_attributes={"color": "black"})

    verify_offer(offer, source, judge=judge)

    assert judge.calls == []


def test_high_confidence_mismatch_is_flagged():
    judge = StubJudge(JudgeResult(is_match=False, confidence=0.9, rationale="Contains whey, not vegan."))
    verdict = verify_offer(make_offer(), make_source(), judge=judge)

    assert verdict.is_verified is False
    assert len(verdict.mismatches) == 1
    assert verdict.mismatches[0].detected_by == "llm"
    assert verdict.mismatches[0].field == "attribute:vegan"
    assert verdict.confidence == 0.9
    assert verdict.method == "rule+llm"


def test_low_confidence_mismatch_is_not_flagged():
    judge = StubJudge(
        JudgeResult(is_match=False, confidence=LLM_CONFIDENCE_THRESHOLD - 0.1, rationale="Not sure.")
    )
    verdict = verify_offer(make_offer(), make_source(), judge=judge)

    assert verdict.is_verified is True
    assert verdict.mismatches == []
    # still recorded for audit even though it didn't trip a mismatch
    assert len(verdict.judged_attributes) == 1


def test_high_confidence_match_is_verified():
    judge = StubJudge(JudgeResult(is_match=True, confidence=0.85, rationale="Consistent with evidence."))
    verdict = verify_offer(make_offer(), make_source(), judge=judge)

    assert verdict.is_verified is True
    assert verdict.mismatches == []
    assert verdict.confidence == 0.85


def test_rule_mismatch_takes_precedence_in_confidence():
    judge = StubJudge(JudgeResult(is_match=True, confidence=0.85, rationale="fine"))
    offer = make_offer(claimed_price=1.00)  # will trip the price rule
    verdict = verify_offer(offer, make_source(), judge=judge)

    assert verdict.is_verified is False
    assert verdict.confidence == 1.0
    assert any(m.detected_by == "rule" for m in verdict.mismatches)
