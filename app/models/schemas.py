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
    # Personal CFO signal: near-term cash need vs. portfolio value (low/medium/high).
    # Biases the decision toward capital preservation when high.
    liquidity_pressure: Literal["low", "medium", "high"] = "low"


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


# --- Phase 4: digital twin & goal-based investing ------------------------


class DigitalTwin(BaseModel):
    """A financial model of the investor — the context every decision reasons against.

    Vestra stops being a stock bot when it can say "preserve cash, you need
    liquidity in 8 months" instead of just "SELL". All monetary fields are INR.
    """

    age: Optional[int] = None
    annual_income: float = 0.0
    monthly_expenses: float = 0.0
    monthly_emi: float = 0.0  # total loan/EMI outflow per month
    monthly_sip: float = 0.0  # recurring investment outflow per month
    emergency_fund: float = 0.0  # liquid cash set aside for emergencies
    tax_bracket: float = 0.0  # marginal rate as a fraction, e.g. 0.30
    risk_profile: Literal["conservative", "moderate", "aggressive"] = "moderate"

    @property
    def monthly_surplus(self) -> float:
        """Income left after expenses, EMIs, and SIPs (monthly)."""
        return self.annual_income / 12.0 - self.monthly_expenses - self.monthly_emi - self.monthly_sip

    @property
    def recommended_emergency_fund(self) -> float:
        """A 6-month expense buffer (expenses + EMIs) is the standard target."""
        return 6.0 * (self.monthly_expenses + self.monthly_emi)


# Goal types Vestra aligns the portfolio against.
GoalType = Literal[
    "retirement",
    "house",
    "education",
    "emergency_fund",
    "wealth_growth",
]


class Goal(BaseModel):
    """A financial goal the portfolio is steered toward."""

    goal_id: Optional[str] = None
    type: GoalType
    name: str = ""
    target_amount: float
    current_amount: float = 0.0
    target_date: Optional[str] = None  # ISO date string
    priority: Literal["low", "medium", "high"] = "medium"

    @property
    def progress_pct(self) -> float:
        if self.target_amount <= 0:
            return 100.0
        return min(100.0, round(self.current_amount / self.target_amount * 100.0, 1))


# --- Phase 5: institutional intelligence ---------------------------------


class CouncilView(BaseModel):
    """One strategy seat's opinion on the analyst's proposed trade."""

    strategy: str  # e.g. "momentum", "contrarian", "risk_averse", "macro"
    action: Literal["BUY", "SELL", "HOLD"]
    rationale: str = ""


class CouncilOpinion(BaseModel):
    """The multi-strategy council's aggregated read.

    ``consensus_action`` is the plurality vote across seats; ``dissent`` (0-1) is
    the fraction of seats that disagree with it -- a measure of how split the room
    is. The CIO weighs strong, low-dissent consensus heavily.
    """

    views: List[CouncilView] = []
    consensus_action: Literal["BUY", "SELL", "HOLD"] = "HOLD"
    dissent: float = 0.0
    rationale: str = ""


class CIODecision(BaseModel):
    """The CIO's final, authoritative verdict over the analyst decision.

    The CIO is the last word: it may pass the analyst decision through, downsize
    it, or veto it to HOLD. ``vetoed`` marks a confidence/risk kill; ``overrode``
    marks the council consensus overriding the analyst's action.
    """

    final_decision: TradeDecision
    vetoed: bool = False
    overrode: bool = False
    rationale: str = ""


# --- Trust layer: plain-English explanation + why-not counterfactuals ----


class Evidence(BaseModel):
    """One piece of evidence behind a recommendation, stated in plain English.

    ``stance`` records whether this signal pushed *toward* deploying/holding the
    action (``supports``), gave a reason for caution (``cautions``), or was merely
    contextual (``neutral``). It drives the colour coding on the trust panel.
    """

    source: str  # e.g. "Signal", "Research", "Market regime", "Risk", "Council", "CIO"
    detail: str
    stance: Literal["supports", "cautions", "neutral"] = "neutral"


class WhyNot(BaseModel):
    """Why an alternative action was *not* the recommendation.

    The decision is one of BUY/SELL/HOLD; the trust layer explains each of the two
    actions that were not chosen, so the user sees the road not taken.
    """

    action: Literal["BUY", "SELL", "HOLD"]
    reason: str


class Explanation(BaseModel):
    """The Trust layer over a finished decision.

    A plain-English account of *why* the system landed on ``action``, the concrete
    ``evidence`` that backed it (drawn from the signal, research, regime, risk,
    council, and CIO), the ``confidence`` it carries, and ``why_not`` counterfactuals
    for the two alternatives. Deterministic and post-hoc -- it narrates state that
    is already computed, so it never changes the decision or the graph flow.
    """

    action: Literal["BUY", "SELL", "HOLD"]
    summary: str = ""
    confidence: float = 0.0
    evidence: List[Evidence] = []
    why_not: List[WhyNot] = []


# --- Decision Review: periodic "what worked / what failed / why" + timeline ----


class DecisionReviewEntry(BaseModel):
    """One ticker's track record over a decision-review period."""

    ticker: str
    decisions: int = 0
    worked: int = 0
    failed: int = 0
    pending: int = 0
    win_rate: float = 0.0  # over *decided* trades only (worked / (worked + failed))
    note: str = ""  # plain-English attribution


class TimelineEvent(BaseModel):
    """One chronological entry in the investor timeline.

    The narrative spine of the review -- "Jan 10: Bought RELIANCE (worked)" --
    ordered oldest-first so it reads as a story.
    """

    ts: str
    ticker: str
    action: Literal["BUY", "SELL", "HOLD"]
    quantity: int = 0
    status: Literal["worked", "failed", "pending", "no_action"] = "pending"
    description: str = ""


class DecisionReview(BaseModel):
    """A periodic review of the agent's decisions: what worked, what failed, why.

    Deterministic roll-up over the agent's memory (past decisions + outcomes):
    overall tallies and win rate, a per-ticker attribution, a chronological
    timeline, and a few plain-English highlights. Builds the trust/learning loop
    the master prompt calls for -- "review all decisions, which worked, which
    failed, why" -- without another LLM call.
    """

    total: int = 0
    completed: int = 0
    losses: int = 0
    pending: int = 0
    win_rate: float = 0.0
    by_ticker: List[DecisionReviewEntry] = []
    timeline: List[TimelineEvent] = []
    highlights: List[str] = []


# --- Risk Stress Testing: named macro shocks applied to the whole book ----


class StressScenario(BaseModel):
    """The projected impact of one named macro shock on the portfolio."""

    name: str  # e.g. "market_drop_5", "rbi_surprise", "sector_crash"
    label: str  # human-readable, e.g. "Market falls 15%"
    value_before: float = 0.0
    value_after: float = 0.0
    loss: float = 0.0  # absolute INR loss (positive == loss)
    loss_pct: float = 0.0  # % of portfolio value lost
    worst_sector: Optional[str] = None  # sector hit hardest in this scenario
    note: str = ""


class StressTestResult(BaseModel):
    """A pre-trade risk stress test: how the book holds up under macro shocks.

    Applies a fixed set of named shocks (broad market drops, an RBI rate
    surprise, a single-sector crash) to current holdings using per-sector
    sensitivities, and reports the projected loss under each. Deterministic --
    the same holdings + prices always yield the same stress test.
    """

    portfolio_value: float = 0.0
    invested_value: float = 0.0  # holdings only, excludes cash
    scenarios: List[StressScenario] = []
    worst_case_loss_pct: float = 0.0
    resilience: Literal["robust", "moderate", "fragile"] = "robust"
    note: str = ""



