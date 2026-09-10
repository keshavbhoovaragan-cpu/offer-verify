"""Data models for offer-verify.

An Offer is a merchant's claim about a product. A SourceRecord is the
authoritative ground truth we check that claim against. A VerificationVerdict
is the pipeline's decision about whether an offer's claims hold up.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.llm_judge import JudgeResult


@dataclass
class Offer:
    offer_id: str
    merchant_id: str
    product_key: str  # join key against SourceRecord.product_key
    product_title: str
    claimed_price: float
    claimed_in_stock: bool
    claimed_attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceRecord:
    product_key: str
    merchant_id: str
    canonical_title: str
    true_price: float
    true_in_stock: bool
    true_attributes: dict[str, Any] = field(default_factory=dict)
    # Free-text evidence (e.g. an ingredient list or product description) that
    # an LLM judge can use to evaluate unstructured claims.
    evidence_text: Optional[str] = None


@dataclass
class Mismatch:
    field: str  # e.g. "price", "in_stock", "attribute:gluten_free"
    claimed: Any
    actual: Any
    detected_by: str  # "rule" | "llm"


@dataclass
class VerificationVerdict:
    offer_id: str
    is_verified: bool
    mismatches: list[Mismatch]
    confidence: float  # 0.0-1.0
    method: str  # "rule" | "rule+llm"
    # (attribute, JudgeResult) for every claim escalated to the LLM tier,
    # win or lose - an audit trail for tuning the confidence threshold and
    # investigating misses later. Empty when method == "rule".
    judged_attributes: list[tuple[str, "JudgeResult"]] = field(default_factory=list)
