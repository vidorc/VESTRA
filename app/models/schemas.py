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


# --- Phase 1: research / reflection / confidence / approval --------------


class ResearchContext(BaseModel):
    """Market research gathered before strategy. Produced by the research node."""

    sentiment: Literal["bullish", "bearish", "neutral"] = "neutral"
    relevant_news: List[str] = []
    sector_impact: str = ""
    historical_context: str = ""
    market_conditions: str = ""
    # 0.0-1.0 signal of how much real data backed this research (live feed vs.
    # static fallback / empty). Consumed by the confidence node.
    data_completeness: float = 0.0


class ReflectionResult(BaseModel):
    """Self-critique of the strategy decision. Produced by the reflection node."""

    is_logical: bool = True
    assumptions: List[str] = []
    missing_data: List[str] = []
    better_alternative: Optional[str] = None
    # Overall verdict on the decision quality.
    verdict: Literal["sound", "acceptable", "questionable"] = "acceptable"


class ConfidenceScore(BaseModel):
    """Aggregated confidence signals computed (rule-based) before approval."""

    decision_confidence: float = 0.0
    risk_confidence: float = 0.0
    data_completeness: float = 0.0
    overall: float = 0.0


# Approval policies governing whether a human must sign off before execution.
ApprovalPolicy = Literal[
    "manual",  # always require human approval
    "approval_required",  # require approval for any non-HOLD trade
    "auto_below_threshold",  # auto-execute only when risk low + confidence high
    "autonomous_sandbox",  # never interrupt (paper/demo only)
]


class ApprovalRequest(BaseModel):
    """A pending/decided human-approval request, mirrored in MongoDB."""

    thread_id: str
    user_id: str
    event_id: Optional[str] = None
    decision: TradeDecision
    confidence: Optional[ConfidenceScore] = None
    reflection: Optional[ReflectionResult] = None
    status: Literal["pending", "approved", "rejected"] = "pending"
    reason: Optional[str] = None


# --- Phase 2: portfolio intelligence -------------------------------------


class HealthFactor(BaseModel):
    """One scored dimension of portfolio health (0-100) with a short note."""

    name: str
    score: float
    weight: float
    note: str = ""


class PortfolioHealth(BaseModel):
    """Overall portfolio health (0-100) plus the factors that produced it."""

    score: float = 0.0
    band: Literal["poor", "fair", "good", "excellent"] = "fair"
    factors: List[HealthFactor] = []


# Market regimes the regime agent can detect.
MarketRegimeType = Literal[
    "bull", "bear", "sideways", "high_volatility", "crisis"
]


class MarketRegime(BaseModel):
    """Detected market regime with a confidence and rationale."""

    regime: MarketRegimeType = "sideways"
    confidence: float = 0.0
    rationale: str = ""


class ScenarioOutcome(BaseModel):
    """A single scenario projection for a proposed trade."""

    name: Literal["best", "base", "worst"]
    probability: float
    expected_return_pct: float
    portfolio_impact: float  # absolute INR impact on portfolio value


class SimulationResult(BaseModel):
    """Best/base/worst scenario projections for a decision."""

    scenarios: List[ScenarioOutcome] = []
    expected_return_pct: float = 0.0
    expected_drawdown_pct: float = 0.0
    risk_score: float = 0.0  # 0-1, higher == riskier
    upside_pct: float = 0.0


class RebalanceAction(BaseModel):
    """A single suggested corrective trade to restore target allocation."""

    ticker: str
    action: Literal["BUY", "SELL"]
    quantity: int
    reason: str


class RebalancePlan(BaseModel):
    """A drift-correction plan derived from target vs. current allocation."""

    drift_detected: bool = False
    actions: List[RebalanceAction] = []
    notes: str = ""


