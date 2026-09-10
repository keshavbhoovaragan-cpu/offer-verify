"""LLM-as-a-rater tier.

For claims a deterministic rule can't decide, mostly unstructured attribute
claims like "gluten-free," "handmade," or "fits most standard doors", ask a
model to judge the claim against whatever evidence text the source record has.

Design decisions (see README.md "LLM judge tier" for the fuller writeup):
  - Evidence handed to the model is exactly SourceRecord.evidence_text - the
    free-text description/ingredient list already on the record. If there's
    no evidence text, there's nothing for the model to reason over, so we
    short-circuit before calling the API at all (see judge_attribute_claim).
  - We ask for a JSON object with is_match, confidence, and rationale rather
    than a bare yes/no, so the verifier can threshold on confidence
    (src/verifier.py) instead of trusting every judgment equally, and so the
    rationale is available to audit later.
  - Model output is parsed defensively: strip markdown fences if present,
    fall back to scanning for the outermost {...} if the model added prose
    around the JSON. If parsing still fails, we return a JudgeResult that
    reads as "unverifiable" (confidence 0.0) rather than raising - a judge
    tier that crashes the whole batch on one malformed response is worse
    than one that abstains.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

import anthropic

from src.schema import Offer, SourceRecord

DEFAULT_JUDGE_MODEL = "claude-sonnet-5"

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


@dataclass
class JudgeResult:
    is_match: bool
    confidence: float  # 0.0-1.0
    rationale: str


def _extract_json(text: str) -> dict[str, Any]:
    """Pull a JSON object out of a model response that may be wrapped in
    markdown fences or have stray prose around it."""
    fence_match = _JSON_FENCE_RE.search(text)
    candidate = fence_match.group(1) if fence_match else text

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    start, end = candidate.find("{"), candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(candidate[start : end + 1])

    raise ValueError(f"no JSON object found in model response: {text!r}")


class LLMJudge:
    def __init__(self, model: str = DEFAULT_JUDGE_MODEL, client: Optional[anthropic.Anthropic] = None):
        self.model = model
        self.client = client or anthropic.Anthropic()

    def judge_attribute_claim(
        self, offer: Offer, source: SourceRecord, attribute: str
    ) -> JudgeResult:
        """Judge a single unstructured attribute claim against source evidence.

        attribute is a key in offer.claimed_attributes that
        check_structured_attributes couldn't resolve directly (i.e. it's not
        in source.true_attributes), e.g. "vegan" or "gluten_free" when the
        source only has free-text evidence, not a structured flag.
        """
        claimed_value = offer.claimed_attributes[attribute]

        if not source.evidence_text:
            # No evidence text means there's nothing to judge the claim
            # against - calling the model would just be asking it to guess.
            # confidence=0.0 signals "unverifiable" to the verifier's
            # thresholding logic, not "confirmed false."
            return JudgeResult(
                is_match=False,
                confidence=0.0,
                rationale="No evidence_text on the source record; claim could not be verified.",
            )

        prompt = f"""You are verifying a merchant's product claim against evidence text.

Attribute: {attribute}
Claimed value: {claimed_value!r}
Evidence text: {source.evidence_text!r}

Does the evidence support the claimed value? Respond with ONLY a JSON object
in exactly this shape - no prose, no markdown code fences, nothing else:

{{"is_match": true or false, "confidence": a number from 0.0 to 1.0, "rationale": "one sentence explaining why"}}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}],
        )

        text = next((block.text for block in response.content if block.type == "text"), "")

        try:
            parsed = _extract_json(text)
            return JudgeResult(
                is_match=bool(parsed["is_match"]),
                confidence=float(parsed["confidence"]),
                rationale=str(parsed["rationale"]),
            )
        except (ValueError, KeyError, TypeError) as e:
            return JudgeResult(
                is_match=False,
                confidence=0.0,
                rationale=f"Could not parse judge response ({e}); raw response: {text!r}",
            )
