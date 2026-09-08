"""Run the verification pipeline over a batch of offers.

    python -m src.cli --offers data/sample_offers.json --source data/sample_source_feed.json
    python -m src.cli --offers data/sample_offers.json --source data/sample_source_feed.json \
        --labeled data/labeled_mismatches.json
"""

import argparse

from src.loader import load_labeled_mismatches, load_offers, load_source_feed
from src.metrics import score
from src.verifier import verify_all


def main():
    parser = argparse.ArgumentParser(description="Run offer verification.")
    parser.add_argument("--offers", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--labeled", required=False, help="Optional labeled_mismatches.json to score against.")
    args = parser.parse_args()

    offers = load_offers(args.offers)
    source_by_key = load_source_feed(args.source)
    verdicts = verify_all(offers, source_by_key)

    for v in verdicts:
        status = "OK" if v.is_verified else "MISMATCH"
        print(f"[{status}] {v.offer_id} (confidence={v.confidence:.2f}, method={v.method})")
        for m in v.mismatches:
            print(f"    - {m.field}: claimed={m.claimed!r} actual={m.actual!r} (via {m.detected_by})")

    if args.labeled:
        labeled_ids = load_labeled_mismatches(args.labeled)
        report = score(verdicts, labeled_ids)
        print("\n--- Score ---")
        print(f"precision={report.precision:.2f} recall={report.recall:.2f} f1={report.f1:.2f}")
        print(f"tp={report.true_positives} fp={report.false_positives} "
              f"fn={report.false_negatives} tn={report.true_negatives}")


if __name__ == "__main__":
    main()
