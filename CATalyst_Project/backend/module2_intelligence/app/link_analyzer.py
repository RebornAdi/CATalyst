"""
link_analyzer.py — the operation-to-wear link (the novel core).

It checks whether an operator-risk driver and a machine-health driver are BOTH
present in the same analysis window. When they are, it reports a correlated,
evidence-backed pattern.

IMPORTANT: this asserts correlation within a shared time window only. It never
claims causation from simulated data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .risk import RiskResult
from .health import HealthResult
from . import config

CORRELATION_NOTE = (
    "Operator behaviour and machine wear are moving together in the same time "
    "window. This is a correlated, evidence-backed pattern, not proven causation."
)


@dataclass
class LinkResult:
    correlation: bool
    note: str = ""
    evidence: List[str] = field(default_factory=list)


def _rank(label: str, order: List[str]) -> int:
    try:
        return order.index(label)
    except ValueError:
        return 0


def analyze_link(risk: RiskResult, health: HealthResult) -> LinkResult:
    risk_order = ["LOW", "MEDIUM", "HIGH"]
    health_order = config.HEALTH_STATUSES  # OK / WARNING / CRITICAL

    risk_ok = _rank(risk.label, risk_order) >= _rank(config.LINK_REQUIRES_RISK_AT_LEAST, risk_order)
    health_ok = _rank(health.status, health_order) >= _rank(config.LINK_REQUIRES_HEALTH_AT_LEAST, health_order)

    if risk_ok and health_ok:
        # Pull the strongest driver from each side for the linking sentence.
        risk_bit = risk.evidence[0] if risk.evidence else f"risk {risk.label}"
        health_bit = health.evidence[0] if health.evidence else f"health {health.status}"
        return LinkResult(
            correlation=True,
            note=CORRELATION_NOTE,
            evidence=[
                f"Correlated in this window: {risk_bit} + {health_bit}",
            ],
        )

    return LinkResult(correlation=False, note="", evidence=[])
