from src.llm_judge import JudgeResult
from src.metrics import score, summarize
from src.schema import Mismatch, VerificationVerdict


def verdict(offer_id, is_verified):
    return VerificationVerdict(
        offer_id=offer_id, is_verified=is_verified, mismatches=[], confidence=1.0, method="rule"
    )


def test_perfect_score():
    verdicts = [verdict("a", is_verified=False), verdict("b", is_verified=True)]
    labeled = {"a"}
    report = score(verdicts, labeled)
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert report.f1 == 1.0


def test_false_negative_hurts_recall_not_precision():
    # "a" is a real mismatch but we didn't catch it (predicted verified=True)
    verdicts = [verdict("a", is_verified=True)]
    labeled = {"a"}
    report = score(verdicts, labeled)
    assert report.recall == 0.0
    assert report.false_negatives == 1


def test_false_positive_hurts_precision_not_recall():
    # "a" isn't actually a mismatch but we flagged it
    verdicts = [verdict("a", is_verified=False)]
    labeled = set()
    report = score(verdicts, labeled)
    assert report.precision == 0.0
    assert report.false_positives == 1


def test_summarize_categorizes_mismatches_and_tracks_llm_escalation():
    price_mismatch = Mismatch(field="price", claimed=1.0, actual=2.0, detected_by="rule")
    stock_mismatch = Mismatch(field="in_stock", claimed=True, actual=False, detected_by="rule")
    structured_mismatch = Mismatch(field="attribute:color", claimed="red", actual="blue", detected_by="rule")
    llm_mismatch = Mismatch(field="attribute:vegan", claimed=True, actual="contains whey", detected_by="llm")

    rule_only_verdict = VerificationVerdict(
        offer_id="a", is_verified=False,
        mismatches=[price_mismatch, stock_mismatch, structured_mismatch],
        confidence=1.0, method="rule",
    )
    llm_verdict = VerificationVerdict(
        offer_id="b", is_verified=False,
        mismatches=[llm_mismatch],
        confidence=0.9, method="rule+llm",
        judged_attributes=[("vegan", JudgeResult(is_match=False, confidence=0.9, rationale="contains whey"))],
    )
    verified_llm_verdict = VerificationVerdict(
        offer_id="c", is_verified=True,
        mismatches=[],
        confidence=0.8, method="rule+llm",
        judged_attributes=[("handmade", JudgeResult(is_match=True, confidence=0.8, rationale="matches"))],
    )

    summary = summarize([rule_only_verdict, llm_verdict, verified_llm_verdict])

    assert summary.total_offers == 3
    assert summary.mismatched_offers == 2
    assert summary.mismatches_by_category == {
        "price": 1, "stock": 1, "structured-attribute": 1, "llm-judged": 1,
    }
    assert summary.offers_escalated_to_llm == 2
    assert summary.offers_resolved_by_rules_only == 1
    assert summary.claims_judged_by_llm == 2
    assert summary.judged_confidence_min == 0.8
    assert summary.judged_confidence_max == 0.9
    assert summary.judged_confidence_buckets["0.7-0.9"] == 1
    assert summary.judged_confidence_buckets["0.9-1.0"] == 1


def test_summarize_with_no_llm_activity():
    summary = summarize([verdict("a", is_verified=True)])

    assert summary.offers_escalated_to_llm == 0
    assert summary.claims_judged_by_llm == 0
    assert summary.judged_confidence_min is None
