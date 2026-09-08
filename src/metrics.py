"""Score the verifier's output against a hand-labeled set of known mismatches.

This turns "does my heuristic actually work" into a number instead of a
feeling, which matters once you start tuning thresholds in src/llm_judge.py
and don't want to just be eyeballing a handful of examples.
"""

from dataclasses import dataclass

from src.schema import VerificationVerdict


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
