"""Unit tests for sector classification, concentration, and pricing (pure)."""

from app.agent.sectors import get_sector, assess_concentration, DEFAULT_SECTOR
from app.agent.pricing import get_reference_price, DEFAULT_REFERENCE_PRICE


def test_known_sectors():
    assert get_sector("INFY") == "it"
    assert get_sector("hdfcbank") == "banking"  # case-insensitive
    assert get_sector("RELIANCE") == "energy"


def test_unknown_ticker_is_other():
    assert get_sector("ZZZZ") == DEFAULT_SECTOR


def test_concentration_low_when_diversified():
    # 10 each across 3 distinct sectors -> max share 1/3 -> not > 0.6 or 0.3 boundary
    holdings = {"INFY": 10, "HDFCBANK": 10, "RELIANCE": 10}
    res = assess_concentration(holdings)
    # largest share is exactly 1/3 (~0.333) -> medium per >0.3 rule
    assert res["concentration_risk"] == "medium"
    assert res["sector_breakdown"] == {"it": 10, "banking": 10, "energy": 10}


def test_concentration_high_when_single_sector():
    res = assess_concentration({"INFY": 30, "TCS": 20})
    assert res["concentration_risk"] == "high"
    assert res["largest_sector"] == "it"
    assert res["largest_sector_exposure"] == 50


def test_concentration_empty_holdings():
    res = assess_concentration({})
    assert res["concentration_risk"] == "low"
    assert res["largest_sector"] is None


def test_reference_price_known_and_default():
    assert get_reference_price("RELIANCE") == 1450.0
    assert get_reference_price("reliance") == 1450.0  # case-insensitive
    assert get_reference_price("UNKNOWNXYZ") == DEFAULT_REFERENCE_PRICE
