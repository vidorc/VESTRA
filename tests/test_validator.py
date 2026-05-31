"""Unit tests for the trade validator (pure, no I/O)."""

from app.models.schemas import RiskAssessment, TradeDecision, ValidationResult
from app.agent.nodes.validator import validate_trade_decision


def _risk(cash=100000.0, limit=10):
    return RiskAssessment(
        concentration_risk="low",
        cash_available=cash,
        safe_trade_limit=limit,
        notes="ok",
    )


def _dec(action, qty, ticker="RELIANCE"):
    return TradeDecision(action=action, ticker=ticker, quantity=qty, reasoning="x")


def test_hold_always_approved():
    res = validate_trade_decision(_dec("HOLD", 0), _risk())
    assert isinstance(res, ValidationResult)
    assert res.approved is True


def test_non_positive_quantity_rejected():
    assert validate_trade_decision(_dec("BUY", 0), _risk()).approved is False


def test_exceeds_safe_trade_limit_rejected():
    res = validate_trade_decision(_dec("BUY", 50), _risk(limit=10))
    assert res.approved is False
    assert "safe trade limit" in res.reason.lower()


def test_buy_insufficient_cash_rejected_using_reference_price():
    # RELIANCE reference price ~1450; 10 * 1450 = 14500 > 5000 cash.
    res = validate_trade_decision(_dec("BUY", 10), _risk(cash=5000.0, limit=20))
    assert res.approved is False
    assert "cash" in res.reason.lower()


def test_buy_affordable_with_explicit_price():
    res = validate_trade_decision(_dec("BUY", 5), _risk(cash=100000.0), price=100.0)
    assert res.approved is True


def test_sell_more_than_owned_rejected():
    res = validate_trade_decision(
        _dec("SELL", 8), _risk(), current_holdings={"RELIANCE": 3}
    )
    assert res.approved is False
    assert "owned" in res.reason.lower()


def test_sell_within_holdings_approved():
    res = validate_trade_decision(
        _dec("SELL", 3), _risk(), current_holdings={"RELIANCE": 10}
    )
    assert res.approved is True
