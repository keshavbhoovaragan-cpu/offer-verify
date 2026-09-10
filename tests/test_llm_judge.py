"""Tests for the LLM judge's parsing/short-circuit logic, using a fake
Anthropic client so these run offline without an API key.
"""

from types import SimpleNamespace

from src.llm_judge import LLMJudge
from src.schema import Offer, SourceRecord


def make_offer(**overrides):
    base = dict(
        offer_id="o1",
        merchant_id="m1",
        product_key="p1",
        product_title="Test product",
        claimed_price=10.0,
        claimed_in_stock=True,
        claimed_attributes={"vegan": True},
    )
    base.update(overrides)
    return Offer(**base)


def make_source(**overrides):
    base = dict(
        product_key="p1",
        merchant_id="m1",
        canonical_title="Test product",
        true_price=10.0,
        true_in_stock=True,
        true_attributes={},
        evidence_text="Ingredients: rolled oats, whey protein isolate, honey.",
    )
    base.update(overrides)
    return SourceRecord(**base)


class FakeMessages:
    def __init__(self, response_text):
        self.response_text = response_text
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.response_text)])


class FakeClient:
    def __init__(self, response_text):
        self.messages = FakeMessages(response_text)


def test_missing_evidence_short_circuits_without_calling_model():
    fake_client = FakeClient(response_text="should never be read")
    judge = LLMJudge(client=fake_client)
    offer = make_offer()
    source = make_source(evidence_text=None)

    result = judge.judge_attribute_claim(offer, source, "vegan")

    assert result.is_match is False
    assert result.confidence == 0.0
    assert fake_client.messages.last_kwargs is None  # never called


def test_parses_plain_json_response():
    fake_client = FakeClient(
        response_text='{"is_match": false, "confidence": 0.95, "rationale": "Whey protein isolate is not vegan."}'
    )
    judge = LLMJudge(client=fake_client)
    result = judge.judge_attribute_claim(make_offer(), make_source(), "vegan")

    assert result.is_match is False
    assert result.confidence == 0.95
    assert "whey" in result.rationale.lower()


def test_parses_json_wrapped_in_markdown_fences():
    fake_client = FakeClient(
        response_text='```json\n{"is_match": true, "confidence": 0.8, "rationale": "Matches."}\n```'
    )
    judge = LLMJudge(client=fake_client)
    result = judge.judge_attribute_claim(make_offer(), make_source(), "vegan")

    assert result.is_match is True
    assert result.confidence == 0.8


def test_parses_json_with_surrounding_prose():
    fake_client = FakeClient(
        response_text='Sure, here is my answer:\n{"is_match": false, "confidence": 0.6, "rationale": "Contains whey."}\nLet me know if you need more.'
    )
    judge = LLMJudge(client=fake_client)
    result = judge.judge_attribute_claim(make_offer(), make_source(), "vegan")

    assert result.is_match is False
    assert result.confidence == 0.6


def test_malformed_response_is_treated_as_unverifiable_not_an_error():
    fake_client = FakeClient(response_text="I'm not sure how to answer that.")
    judge = LLMJudge(client=fake_client)
    result = judge.judge_attribute_claim(make_offer(), make_source(), "vegan")

    assert result.is_match is False
    assert result.confidence == 0.0
    assert "could not parse" in result.rationale.lower()


def test_sends_claimed_value_and_evidence_in_the_prompt():
    fake_client = FakeClient(
        response_text='{"is_match": false, "confidence": 0.9, "rationale": "no"}'
    )
    judge = LLMJudge(client=fake_client)
    offer = make_offer(claimed_attributes={"vegan": True})
    source = make_source(evidence_text="Ingredients: whey protein isolate.")

    judge.judge_attribute_claim(offer, source, "vegan")

    prompt = fake_client.messages.last_kwargs["messages"][0]["content"]
    assert "vegan" in prompt
    assert "True" in prompt
    assert "whey protein isolate" in prompt
