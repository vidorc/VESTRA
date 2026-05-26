from typing import Dict, List, Literal, Optional
from pydantic import BaseModel


class MarketEvent(BaseModel):
    ticker: str
    price_change_percent: float
    breaking_news_summary: str


class InvestorProfile(BaseModel):
    user_id: str
    risk_tolerance: Literal[
        "conservative",
        "moderate",
        "aggressive"
    ]
    cash_balance: float
    holdings: Dict[str, int]
    target_allocation: Dict[str, float]


class SignalAssessment(BaseModel):
    event_type: Literal[
        "macro",
        "company",
        "earnings",
        "commodity",
        "geopolitical"
    ]
    severity: Literal[
        "low",
        "medium",
        "high",
        "critical"
    ]
    impacted_assets: List[str]


class RiskAssessment(BaseModel):
    concentration_risk: str
    cash_available: float
    safe_trade_limit: int
    notes: Optional[str] = None


class TradeDecision(BaseModel):
    action: Literal[
        "BUY",
        "SELL",
        "HOLD"
    ]
    ticker: str
    quantity: int
    reasoning: str


class ValidationResult(BaseModel):
    approved: bool
    reason: str


class AuditLog(BaseModel):
    agent_name: str
    timestamp: str
    action: str
    payload: dict
