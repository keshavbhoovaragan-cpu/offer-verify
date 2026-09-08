from src.loader import load_labeled_mismatches, load_offers, load_source_feed

OFFERS_PATH = "data/sample_offers.json"
SOURCE_PATH = "data/sample_source_feed.json"
LABELED_PATH = "data/labeled_mismatches.json"


def test_load_offers():
    offers = load_offers(OFFERS_PATH)
    assert len(offers) == 4
    assert offers[0].offer_id == "offer_001"


def test_load_source_feed_keyed_by_product_key():
    source_by_key = load_source_feed(SOURCE_PATH)
    assert "sku_hoodie_black_m" in source_by_key
    assert source_by_key["sku_hoodie_black_m"].true_price == 39.99


def test_load_labeled_mismatches():
    labeled = load_labeled_mismatches(LABELED_PATH)
    assert "offer_002" in labeled
    assert "offer_004" in labeled
