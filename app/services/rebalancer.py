"""Portfolio Rebalancer service.

Detects allocation **drift** between an investor's `target_allocation` and their
current holdings, and produces a corrective :class:`~app.models.schemas.RebalancePlan`
(BUY/SELL actions that move each position back toward its target weight).

Like the other Phase 2 analytics this is **deterministic and rule-based**, with a
pure core (:func:`compute_rebalance_plan`, prices passed in) and a thin async
wrapper (:func:`preview_rebalance`) that resolves prices from the market provider.

Method
------
* Target weights are normalized over the tickers named in `target_allocation`
  (they need not sum to 100 — the remainder is treated as a cash sleeve and the
  equity sleeve is rebalanced to the named weights).
* Current weights come from `holdings × price` as a share of total equity value.
* A position whose weight drifts from target by at least `drift_threshold_pct`
  (default 5 points) gets a corrective action sized to restore the target value.
* A held ticker absent from the target has an implicit target of 0% → SELL all.
"""

from typing import Dict, List

from app.models.schemas import RebalanceAction, RebalancePlan

_DEFAULT_DRIFT_THRESHOLD_PCT = 5.0


def compute_rebalance_plan(
    holdings: Dict[str, int],
    target_allocation: Dict[str, float],
    prices: Dict[str, float],
    drift_threshold_pct: float = _DEFAULT_DRIFT_THRESHOLD_PCT,
) -> RebalancePlan:
    """Pure drift detection + correction. Returns a :class:`RebalancePlan`."""
    holdings = {k.upper(): v for k, v in (holdings or {}).items()}
    targets = {k.upper(): float(v) for k, v in (target_allocation or {}).items()}

    if not targets:
        return RebalancePlan(drift_detected=False, actions=[], notes="No target allocation set.")

    # Current equity value per ticker and in total.
    values = {t: prices.get(t, 0.0) * q for t, q in holdings.items()}
    total_value = sum(values.values())
    if total_value <= 0:
        return RebalancePlan(
            drift_detected=False, actions=[], notes="No priced holdings to rebalance."
        )

    # Normalize target weights over named tickers -> percentages summing to 100.
    target_sum = sum(targets.values())
    if target_sum <= 0:
        return RebalancePlan(drift_detected=False, actions=[], notes="Target allocation is empty.")
    target_pct = {t: (w / target_sum) * 100.0 for t, w in targets.items()}

    # Consider every ticker that appears in either holdings or targets.
    universe = set(holdings) | set(targets)
    actions: List[RebalanceAction] = []

    for ticker in sorted(universe):
        price = prices.get(ticker, 0.0)
        current_value = values.get(ticker, 0.0)
        current_pct = (current_value / total_value) * 100.0
        tgt_pct = target_pct.get(ticker, 0.0)  # absent from target -> 0%
        drift = current_pct - tgt_pct

        if abs(drift) < drift_threshold_pct:
            continue
        if price <= 0:
            continue  # cannot size an action without a price

        target_value = (tgt_pct / 100.0) * total_value
        delta_value = target_value - current_value
        qty = int(round(delta_value / price))
        if qty == 0:
            continue

        if qty > 0:
            actions.append(
                RebalanceAction(
                    ticker=ticker,
                    action="BUY",
                    quantity=qty,
                    reason=f"Underweight: {current_pct:.0f}% vs {tgt_pct:.0f}% target.",
                )
            )
        else:
            actions.append(
                RebalanceAction(
                    ticker=ticker,
                    action="SELL",
                    quantity=-qty,
                    reason=f"Overweight: {current_pct:.0f}% vs {tgt_pct:.0f}% target.",
                )
            )

    if not actions:
        return RebalancePlan(
            drift_detected=False, actions=[], notes="Portfolio is within target tolerances."
        )
    return RebalancePlan(
        drift_detected=True,
        actions=actions,
        notes=f"{len(actions)} corrective action(s) at {drift_threshold_pct:.0f}pt drift threshold.",
    )


async def preview_rebalance(
    holdings: Dict[str, int],
    target_allocation: Dict[str, float],
    drift_threshold_pct: float = _DEFAULT_DRIFT_THRESHOLD_PCT,
) -> RebalancePlan:
    """Resolve prices from the market provider and compute a plan. Never raises."""
    from app.data.market.provider import get_market_data_provider

    provider = get_market_data_provider()
    prices: Dict[str, float] = {}
    universe = set((holdings or {})) | set((target_allocation or {}))
    for ticker in universe:
        try:
            prices[ticker.upper()] = provider.get_cached_price(ticker)
        except Exception:
            prices[ticker.upper()] = 0.0

    return compute_rebalance_plan(
        holdings, target_allocation, prices, drift_threshold_pct=drift_threshold_pct
    )


__all__ = ["compute_rebalance_plan", "preview_rebalance"]
