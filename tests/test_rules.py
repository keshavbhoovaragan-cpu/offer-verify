import pytest

from src.rules import check_price, check_stock, check_structured_attributes
from src.schema import Offer, SourceRecord


def make_offer(**overrides):
    base = dict(
        offer_id="o1",
        merchant_id="m1",
        product_key="p1",
        product_title="Test product",
        claimed_price=10.0,
        claimed_in_stock=True,
        claimed_attributes={},
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
    )
    base.update(overrides)
    return SourceRecord(**base)


def test_price_within_tolerance_is_fine():
    offer = make_offer(claimed_price=10.10)
    source = make_source(true_price=10.00)
    assert check_price(offer, source) is None


def test_price_outside_tolerance_is_a_mismatch():
    offer = make_offer(claimed_price=25.00)
    source = make_source(true_price=44.99)
    mismatch = check_price(offer, source)
    assert mismatch is not None
    assert mismatch.field == "price"
    assert mismatch.claimed == 25.00
    assert mismatch.actual == 44.99


def test_stock_mismatch_is_detected():
    offer = make_offer(claimed_in_stock=True)
    source = make_source(true_in_stock=False)
    mismatch = check_stock(offer, source)
    assert mismatch is not None
    assert mismatch.field == "in_stock"
    assert mismatch.claimed is True
    assert mismatch.actual is False


def test_stock_match_is_not_a_mismatch():
    offer = make_offer(claimed_in_stock=True)
    source = make_source(true_in_stock=True)
    mismatch = check_stock(offer, source)
    assert mismatch is None

def test_check_structured_attributes_not_implemented_yet():
    # Remove this test once you implement it in ROADMAP.md step 2.
    with pytest.raises(NotImplementedError):
        check_structured_attributes(make_offer(), make_source())