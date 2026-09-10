# Roadmap / suggested commit order

This is a suggestion, not a script. The point of committing in real stages is
that your git history should show actual incremental thinking, not one giant
dump. Adjust as you go, and it's fine (good, even) if your real order differs
from this once you hit something the plan didn't anticipate.

- [x] `0. scaffold` - project structure, schema, loader, price rule, metrics,
      CLI, sample data. (This is the starting point in this repo.)
- [x] `1. stock rule` - implement the in-stock mismatch check in `src/rules.py`.
      Write the test first in `tests/test_rules.py`.
- [x] `2. attribute rule (structured)` - implement exact/fuzzy matching for
      structured attributes (e.g. color, size) where a simple string or
      numeric comparison is enough. Not every attribute claim needs an LLM.
- [x] `3. labeled mismatch set` - expand `data/labeled_mismatches.json` with
      more cases, including ones your current rules get wrong. This is what
      makes your precision/recall numbers mean something later.
- [x] `4. LLM-as-judge, first pass` - implement `src/llm_judge.py` for the
      unstructured attribute claims (e.g. "gluten-free," "handmade") that
      rules can't decide. Start with a plain prompt and see how it does
      before optimizing anything.
      **Caveat**: built without API credentials available, so verified via a
      mocked-client test suite (`tests/test_llm_judge.py`), not a live call
      against offer_005. Run it for real once you have a key - see README.md
      "Confidence threshold."
- [x] `5. confidence thresholding` - decide how the LLM's output becomes a
      confidence score, and tune the threshold against `labeled_mismatches.json`.
      Write down what you tried and why the final threshold won.
      **Caveat**: `LLM_CONFIDENCE_THRESHOLD = 0.7` in `src/verifier.py` is a
      reasoned default (see README.md), not yet tuned against real judge
      output for the same reason as step 4 - no API key in this environment.
- [ ] `6. precision heuristics` - once you have real errors from step 5, add
      whatever heuristics reduce false positives/negatives (e.g. requiring two
      independent signals before flagging a high-confidence mismatch).
      Blocked on step 5 actually running against real data first - there are
      no real false positives/negatives to look at yet.
- [x] `7. batch reporting` - extend `src/cli.py` to output a summary report
      (mismatch rate by category, confidence distribution, etc.) instead of
      just per-offer verdicts.
- [x] `8. write up results` - update the README with your actual
      precision/recall numbers and what you learned. This is the paragraph
      you'll actually talk about in an interview.
      **Caveat**: the design writeup and threshold rationale are in
      README.md; the "Current results" table's LLM-tier row is still a
      placeholder pending a live run (see step 4/5 caveats).

Optional, if you want to go further:
- [ ] CI via GitHub Actions running `pytest` on push
- [ ] A small FastAPI wrapper so it's a real service, not just a CLI
