# offer-verify

A small commercial-claim verification pipeline: given a merchant's claims about a
product (price, stock, attributes) and an authoritative source-of-truth feed, decide
whether each claim is accurate, and flag the ones that aren't.

This is the same shape of problem that shows up anywhere a platform surfaces
third-party claims to users and needs to catch mismatches before they do:
shopping/ads surfaces checking merchant feeds, marketplaces checking seller
listings, review platforms checking business hours or menus, etc.

## Why it's built this way

Real verification systems don't send every claim to an LLM, that's slow and
expensive. They run cheap deterministic checks first (does the price match
within tolerance? does the stock flag match?) and only escalate the genuinely
ambiguous claims, the ones language has to interpret ("gluten-free," "handmade,"
"fits most doors") to a model acting as a rater. This repo follows that same
two-tier design:

1. **Rule tier** (`src/rules.py`) - fast, deterministic, exact-match or
   tolerance-based checks. Cheap, explainable, no API calls.
2. **LLM-judge tier** (`src/llm_judge.py`) - for claims that aren't structured
   enough for a rule to decide. This is where you write the prompt, decide
   what evidence to hand the model, and figure out how to turn its output into
   a confidence score you can threshold on.
3. **Verifier** (`src/verifier.py`) - orchestrates the two tiers and produces a
   final verdict per offer.
4. **Metrics** (`src/metrics.py`) - precision/recall/F1 against a labeled set of
   known mismatches, so "does my heuristic actually work" is a number, not a
   feeling.

## What's implemented vs. what's yours to build

Implemented:
- Data models (`src/schema.py`)
- Loading and joining offers against the source feed (`src/loader.py`)
- Rule-tier checks: price tolerance, stock match, structured attribute match (`src/rules.py`)
- The LLM-as-judge tier for unstructured attribute claims (`src/llm_judge.py`)
- Verifier wiring + confidence thresholding between the two tiers (`src/verifier.py`)
- The metrics harness, including a batch summary report (`src/metrics.py`)
- A CLI to run the pipeline, with per-offer verdicts and a batch summary (`src/cli.py`)

Open item, see "Confidence threshold" below: the threshold is a reasoned
default, not yet tuned against real judge output, because this was built in
a sandbox with no `ANTHROPIC_API_KEY` configured. The judge and its
thresholding logic are covered by tests against a mocked client
(`tests/test_llm_judge.py`, `tests/test_verifier.py`), but nobody has run
`python -m src.cli ... --labeled data/labeled_mismatches.json` against the
real model yet. See "Running it" for how to do that.

## LLM judge tier

`src/llm_judge.py` handles attribute claims `check_structured_attributes`
can't resolve - the key isn't in `source.true_attributes` at all, so no rule
ever sees it (e.g. `vegan`, `gluten_free` when only free-text evidence
exists). Design choices:

- **Evidence handed to the model**: exactly `source.evidence_text`, nothing
  more. It's the only ground truth available for unstructured claims in this
  schema, and augmenting it with anything else would mean inventing
  evidence that isn't actually there.
- **Missing evidence short-circuits before the API call.** If
  `evidence_text` is `None` or empty, there's nothing to judge the claim
  against, so `judge_attribute_claim` returns immediately with
  `confidence=0.0` rather than asking the model to guess. That confidence
  value is what lets the verifier's thresholding logic (below) treat it as
  "unverifiable" instead of "confirmed false."
- **Output shape**: `{"is_match": bool, "confidence": float, "rationale": str}`
  rather than a bare yes/no, so the verifier has something to threshold on
  and the rationale is preserved for later auditing (`verdict.judged_attributes`).
- **Parsing is defensive**: the model may wrap the JSON in markdown fences or
  add prose around it. `_extract_json` strips fences, then falls back to the
  outermost `{...}` span. If parsing still fails, the result reads as
  unverifiable (`confidence=0.0`) rather than raising - one malformed
  response shouldn't crash a batch run.
- **Model**: `claude-sonnet-5`, thinking disabled. This is a short,
  single-shot classification call (return one JSON object), not an agentic
  or long-horizon task, so a cheaper model with no reasoning overhead is the
  right fit rather than defaulting to the most capable model.

## Confidence threshold

`LLM_CONFIDENCE_THRESHOLD` in `src/verifier.py` is currently **0.7**. Below
that, a judge's `is_match=False` is treated as "the model wasn't sure" and
the claim is left unverified rather than flagged as a mismatch - a
low-confidence "no" and a high-confidence "no" are different claims, and
collapsing them trades false negatives for false positives without actually
improving anything.

This value is a reasoned starting point, not yet measured: 0.7 sits above
"more likely than not" but below "the model is basically certain," which
seemed like a defensible place to separate "confidently wrong" from "just
unsure" without more data. It has **not** been tuned against real judge
output - the sandbox this was built in has no API credentials, so
`judge_attribute_claim` has only been exercised against a mocked client (see
`tests/test_llm_judge.py`). If you have an `ANTHROPIC_API_KEY`, the way to
tune it for real:

```bash
export ANTHROPIC_API_KEY=sk-...
python -m src.cli --offers data/sample_offers.json --source data/sample_source_feed.json \
    --labeled data/labeled_mismatches.json
```

Look at the confidence distribution in the summary output and the `--labeled`
score. If the judge is producing high-confidence `is_match=False` calls that
aren't in `labeled_mismatches.json` (false positives), raise the threshold.
If real mismatches are landing in the "unverifiable" bucket because the
judge hedged (false negatives), lower it. Whatever you land on, update this
section with the number and what you saw that justified it.

## Current results

Rule-tier only, against the 7 sample offers in `data/`:

| Metric | Value |
|---|---|
| Precision | 1.00 |
| Recall | 0.80 |
| F1 | 0.89 |

The rule tier catches every price and stock mismatch, with zero false positives.
It structurally can't catch claims that need interpreting free text: `offer_005`
claims `vegan: true`, but the ingredient evidence shows whey protein isolate.
Since `vegan` never appears as a structured attribute, no rule sees it, that's
exactly the gap the LLM judge tier is meant to close.

**With the LLM judge tier wired in**: not yet measured end-to-end against
the real model (see "Confidence threshold" above for why). The code path
that should catch `offer_005` - `vegan: true` claimed, evidence shows whey
protein isolate - is implemented and unit-tested against a mocked client,
but the actual precision/recall/F1 with a live judge, and what it catches or
misses beyond `offer_005`, is unmeasured. Run the command above with a real
API key and fill in this table with what you find.

## Running it

```bash
pip install -r requirements.txt
pytest                     # should pass out of the box, no API key needed - the LLM tier is mocked in tests

# Rule tier only (no offer in the sample data needs the LLM tier except offer_005):
python -m src.cli --offers data/sample_offers.json --source data/sample_source_feed.json

# Full pipeline including the LLM judge tier - needs ANTHROPIC_API_KEY:
export ANTHROPIC_API_KEY=sk-...
python -m src.cli --offers data/sample_offers.json --source data/sample_source_feed.json \
    --labeled data/labeled_mismatches.json
```

The CLI prints a per-offer verdict, then (with `--labeled`) a precision/recall/F1
score, then a batch summary: mismatch rate by category (price / stock /
structured-attribute / llm-judged), how many offers were escalated to the LLM
tier vs. resolved by rules alone, and the confidence distribution of judged
claims.

## Project structure

```
offer-verify/
  data/
    sample_offers.json          merchant-claimed data ("offers")
    sample_source_feed.json     authoritative ground truth
    labeled_mismatches.json     hand-labeled offer_ids that are known mismatches, for scoring
  src/
    schema.py       data models
    loader.py        loads + joins offers to source records
    rules.py         deterministic verification rules
    llm_judge.py      LLM-as-a-rater tier for unstructured attribute claims
    verifier.py       orchestrates rules + llm_judge into a verdict, confidence thresholding
    metrics.py        precision/recall/F1 against labeled_mismatches.json, batch summary report
    cli.py            entry point
  tests/
    test_rules.py
    test_loader.py
    test_metrics.py
    test_llm_judge.py    LLM judge parsing/short-circuit logic, against a mocked client
    test_verifier.py     LLM-tier wiring + confidence thresholding, against a stub judge
```
