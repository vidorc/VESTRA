"""Goal-based investing service.

Turns an investor's goals + digital twin into signals the rest of the system
reasons against, so Vestra can say "preserve cash, you need liquidity in 8
months" rather than just "SELL". Two deterministic outputs:

* :func:`goal_alignment_score` (0-100) — how well-funded and on-track the goals
  are, weighted by priority. Feeds the Portfolio Health Engine's previously-stubbed
  ``goal_alignment`` factor.
* :func:`liquidity_need` — a near-term cash requirement derived from goals due
  soon plus any emergency-fund shortfall. Downstream agents (risk, CIO) can use
  this to bias toward capital preservation.

Pure and rule-based: no I/O, fully unit-testable. Dates are parsed leniently;
anything unparseable is treated as "no deadline" rather than raising.
"""

from datetime import date, datetime
from typing import List, Optional

from app.models.schemas import DigitalTwin, Goal

_PRIORITY_WEIGHT = {"high": 3.0, "medium": 2.0, "low": 1.0}
# A goal due within this horizon counts toward near-term liquidity need.
_NEAR_TERM_MONTHS = 12


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None


def _months_until(target: Optional[date], today: date) -> Optional[float]:
    if target is None:
        return None
    return (target.year - today.year) * 12 + (target.month - today.month) + (target.day - today.day) / 30.0


def goal_alignment_score(goals: List[Goal]) -> float:
    """Priority-weighted average funding progress across goals (0-100).

    Returns a neutral 50.0 when there are no goals (so health scoring is unchanged
    until the user sets goals).
    """
    if not goals:
        return 50.0
    total_w = 0.0
    acc = 0.0
    for g in goals:
        w = _PRIORITY_WEIGHT.get(g.priority, 2.0)
        acc += w * g.progress_pct
        total_w += w
    return round(acc / total_w, 1) if total_w else 50.0


def liquidity_need(
    goals: List[Goal],
    twin: Optional[DigitalTwin] = None,
    today: Optional[date] = None,
) -> float:
    """Near-term cash requirement (INR): unfunded goals due soon + emergency shortfall.

    ``today`` is injectable for deterministic tests.
    """
    today = today or date.today()
    need = 0.0

    for g in goals or []:
        months = _months_until(_parse_date(g.target_date), today)
        if months is not None and 0 <= months <= _NEAR_TERM_MONTHS:
            shortfall = max(0.0, g.target_amount - g.current_amount)
            need += shortfall

    # Emergency-fund shortfall is always a near-term liquidity need.
    if twin is not None:
        need += max(0.0, twin.recommended_emergency_fund - twin.emergency_fund)

    return round(need, 2)


def liquidity_pressure(
    goals: List[Goal],
    twin: Optional[DigitalTwin] = None,
    portfolio_value: float = 0.0,
    today: Optional[date] = None,
) -> str:
    """Classify liquidity pressure as low/medium/high relative to portfolio value.

    Used to bias decisions toward preservation when near-term cash needs are large
    relative to investable assets.
    """
    need = liquidity_need(goals, twin, today=today)
    if need <= 0:
        return "low"
    if portfolio_value <= 0:
        return "high"  # cash needed but nothing invested to draw on
    ratio = need / portfolio_value
    if ratio >= 0.5:
        return "high"
    if ratio >= 0.2:
        return "medium"
    return "low"


__all__ = ["goal_alignment_score", "liquidity_need", "liquidity_pressure"]
