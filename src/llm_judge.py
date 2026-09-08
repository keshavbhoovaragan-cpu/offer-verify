"""LLM-as-a-rater tier.

For claims a deterministic rule can't decide, mostly unstructured attribute
claims like "gluten-free," "handmade," or "fits most standard doors", ask a
model to judge the claim against whatever evidence text the source record has.

This is intentionally unimplemented. When you build it, you'll need to decide:
  - What evidence do you actually hand the model? (SourceRecord.evidence_text
    is there for this, but is it enough, or do you need more context?)
  - What do you ask for back? A yes/no? A confidence score? A rationale you
    can log for debugging?
  - How do you turn a free-text model response into something
    src/verifier.py can threshold on?
  - What happens when the model is unsure, or when evidence_text is missing?

None of these have one right answer. Write down what you chose and why,
that's the part worth being able to talk through later.
"""

from dataclasses import dataclass

from src.schema import Offer, SourceRecord


@dataclass
class JudgeResult:
    is_match: bool
    confidence: float  # 0.0-1.0
    rationale: str


class LLMJudge:
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.model = model

    def judge_attribute_claim(
        self, offer: Offer, source: SourceRecord, attribute: str
    ) -> JudgeResult:
        """TODO: implement this.

        attribute is a key in offer.claimed_attributes that check_structured_attributes
        couldn't resolve directly (e.g. "gluten_free"). Use source.evidence_text
        as the evidence to judge the claim against.

        See ROADMAP.md step 4 for where this fits in the build order.
        """
        raise NotImplementedError("judge_attribute_claim is not implemented yet - see ROADMAP.md step 4")
