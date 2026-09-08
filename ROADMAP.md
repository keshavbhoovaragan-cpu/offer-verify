# Roadmap / suggested commit order

This is a suggestion, not a script. The point of committing in real stages is
that your git history should show actual incremental thinking, not one giant
dump. Adjust as you go, and it's fine (good, even) if your real order differs
from this once you hit something the plan didn't anticipate.

- [x] `0. scaffold` - project structure, schema, loader, price rule, metrics,
      CLI, sample data. (This is the starting point in this repo.)
- [ ] `1. stock rule` - implement the in-stock mismatch check in `src/rules.py`.
      Write the test first in `tests/test_rules.py`.
- [ ] `2. attribute rule (structured)` - implement exact/fuzzy matching for
      structured attributes (e.g. color, size) where a simple string or
      numeric comparison is enough. Not every attribute claim needs an LLM.
- [ ] `3. labeled mismatch set` - expand `data/labeled_mismatches.json` with
      more cases, including ones your current rules get wrong. This is what
      makes your precision/recall numbers mean something later.
- [ ] `4. LLM-as-judge, first pass` - implement `src/llm_judge.py` for the
      unstructured attribute claims (e.g. "gluten-free," "handmade") that
      rules can't decide. Start with a plain prompt and see how it does
      before optimizing anything.
- [ ] `5. confidence thresholding` - decide how the LLM's output becomes a
      confidence score, and tune the threshold against `labeled_mismatches.json`.
      Write down what you tried and why the final threshold won.
- [ ] `6. precision heuristics` - once you have real errors from step 5, add
      whatever heuristics reduce false positives/negatives (e.g. requiring two
      independent signals before flagging a high-confidence mismatch).
- [ ] `7. batch reporting` - extend `src/cli.py` to output a summary report
      (mismatch rate by category, confidence distribution, etc.) instead of
      just per-offer verdicts.
- [ ] `8. write up results` - update the README with your actual
      precision/recall numbers and what you learned. This is the paragraph
      you'll actually talk about in an interview.

Optional, if you want to go further:
- [ ] CI via GitHub Actions running `pytest` on push
- [ ] A small FastAPI wrapper so it's a real service, not just a CLI
