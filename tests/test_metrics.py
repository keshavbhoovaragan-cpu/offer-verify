from src.metrics import score
from src.schema import VerificationVerdict


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
