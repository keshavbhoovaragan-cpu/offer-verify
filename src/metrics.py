"""Score the verifier's output against a hand-labeled set of known mismatches,
and summarize a batch run for reporting.

This turns "does my heuristic actually work" into a number instead of a
feeling, which matters once you start tuning thresholds in src/llm_judge.py
and don't want to just be eyeballing a handful of examples.
"""

from dataclasses import dataclass, field

from src.schema import VerificationVerdict

# Confidence buckets for reporting the judge's confidence distribution,
# centered on LLM_CONFIDENCE_THRESHOLD (0.7) so it's easy to see how much
# mass sits on either side of the cutoff.
_CONFIDENCE_BUCKETS = ["<0.5", "0.5-0.7", "0.7-0.9", "0.9-1.0"]


@dataclass
class ScoreReport:
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1: float


def score(verdicts: list[VerificationVerdict], labeled_mismatch_ids: set[str]) -> ScoreReport:
    tp = fp = fn = tn = 0

    for v in verdicts:
        predicted_mismatch = not v.is_verified
        actually_mismatch = v.offer_id in labeled_mismatch_ids

        if predicted_mismatch and actually_mismatch:
            tp += 1
        elif predicted_mismatch and not actually_mismatch:
            fp += 1
        elif not predicted_mismatch and actually_mismatch:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return ScoreReport(
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def _categorize(field_name: str, detected_by: str) -> str:
    if field_name == "price":
        return "price"
    if field_name == "in_stock":
        return "stock"
    if field_name.startswith("attribute:"):
        return "llm-judged" if detected_by == "llm" else "structured-attribute"
    return field_name  # unrecognized, report as-is rather than silently dropping


def _bucket(confidence: float) -> str:
    if confidence < 0.5:
        return "<0.5"
    if confidence < 0.7:
        return "0.5-0.7"
    if confidence < 0.9:
        return "0.7-0.9"
    return "0.9-1.0"


@dataclass
class BatchSummary:
    total_offers: int
    mismatched_offers: int
    mismatch_rate: float
    mismatches_by_category: dict[str, int]
    offers_escalated_to_llm: int
    offers_resolved_by_rules_only: int
    claims_judged_by_llm: int
    judged_confidence_min: float | None
    judged_confidence_max: float | None
    judged_confidence_mean: float | None
    judged_confidence_buckets: dict[str, int] = field(default_factory=dict)


def summarize(verdicts: list[VerificationVerdict]) -> BatchSummary:
    total_offers = len(verdicts)
    mismatched_offers = sum(1 for v in verdicts if not v.is_verified)

    mismatches_by_category: dict[str, int] = {}
    for v in verdicts:
        for m in v.mismatches:
            category = _categorize(m.field, m.detected_by)
            mismatches_by_category[category] = mismatches_by_category.get(category, 0) + 1

    escalated = [v for v in verdicts if v.judged_attributes]
    all_confidences = [result.confidence for v in verdicts for _, result in v.judged_attributes]

    confidence_buckets = {b: 0 for b in _CONFIDENCE_BUCKETS}
    for c in all_confidences:
        confidence_buckets[_bucket(c)] += 1

    return BatchSummary(
        total_offers=total_offers,
        mismatched_offers=mismatched_offers,
        mismatch_rate=(mismatched_offers / total_offers) if total_offers else 0.0,
        mismatches_by_category=mismatches_by_category,
        offers_escalated_to_llm=len(escalated),
        offers_resolved_by_rules_only=total_offers - len(escalated),
        claims_judged_by_llm=len(all_confidences),
        judged_confidence_min=min(all_confidences) if all_confidences else None,
        judged_confidence_max=max(all_confidences) if all_confidences else None,
        judged_confidence_mean=(sum(all_confidences) / len(all_confidences)) if all_confidences else None,
        judged_confidence_buckets=confidence_buckets,
    )
