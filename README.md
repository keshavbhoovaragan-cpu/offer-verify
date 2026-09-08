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

Implemented, so the project runs end to end from the start:
- Data models (`src/schema.py`)
- Loading and joining offers against the source feed (`src/loader.py`)
- One working rule: price-tolerance matching (`src/rules.py`)
- The metrics harness (`src/metrics.py`)
- A CLI to run the pipeline (`src/cli.py`)

Left as TODOs for you, on purpose, see `ROADMAP.md` for a suggested commit-by-commit
order:
- The stock-mismatch and attribute-mismatch rules
- The LLM-as-judge tier for fuzzy attribute claims
- Tuning the confidence threshold against the labeled mismatch set in `data/labeled_mismatches.json`
- Whatever you find missing once you try to make precision/recall actually good

## Running it

```bash
pip install -r requirements.txt
pytest                     # should pass out of the box
python -m src.cli --offers data/sample_offers.json --source data/sample_source_feed.json
```

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
    llm_judge.py      LLM-as-a-rater tier (stub, see TODOs)
    verifier.py       orchestrates rules + llm_judge into a verdict
    metrics.py        precision/recall/F1 against labeled_mismatches.json
    cli.py            entry point
  tests/
    test_rules.py
    test_loader.py
    test_metrics.py
```
