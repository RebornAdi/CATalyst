"""
risk.py — evaluate OPERATOR behaviour and produce a deterministic risk score.

Drivers considered:
  * idle time vs baseline (ratio + z-score)
  * harsh / high-load cycles in the recent window (count)
  * safety events (seatbelt deviation during high load, or explicit safety_alert)

Output is a RiskResult with a 0..100 score, a label, and structured evidence.
No LLM here — pure computation, per the module rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict

from .schemas import TelemetryReading, EvidenceDetail
from .baseline import zscore
from . import config


@dataclass
class RiskResult:
    label: str                       # LOW / MEDIUM / HIGH
    score: float                     # 0..100
    evidence: List[str] = field(default_factory=list)
    detail: List[EvidenceDetail] = field(default_factory=list)
    drivers: Dict[str, float] = field(default_factory=dict)  # named contributions
    # signals that fired, used later for confidence corroboration counting
    fired_signals: List[str] = field(default_factory=list)


def _count_harsh_cycles(current: TelemetryReading, history: List[TelemetryReading]) -> int:
    """
    Count harsh/high-load cycles in the recent window.

    Module 1 gives load as a categorical (HIGH). We count HIGH-load readings in
    the recent history plus the current one as a proxy for harsh cycles.
    """
    window = history[-12:] if history else []
    count = sum(1 for h in window if h.load == "HIGH")
    if current.load == "HIGH":
        count += 1
    return count


def _label_for_score(score: float) -> str:
    for threshold, label in config.RISK_LABEL_BANDS:
        if score >= threshold:
            return label
    return "LOW"


def evaluate_risk(
    current: TelemetryReading,
    history: List[TelemetryReading],
    op_base: Dict[str, float],
) -> RiskResult:
    res = RiskResult(label="LOW", score=0.0)

    # ---- 1. Idle time ----
    base_idle = op_base["idle_minutes"] or 1.0
    idle_ratio = current.idle_minutes / base_idle if base_idle else 1.0
    idle_z = zscore(current.idle_minutes, op_base["idle_minutes"], op_base.get("idle_std", 0.0))

    idle_contribution = 0.0
    if idle_ratio >= config.IDLE_RATIO_HIGH:
        idle_contribution = 40.0
        res.evidence.append(
            f"Idle time {current.idle_minutes:.0f} min = {idle_ratio:.1f}x baseline ({base_idle:.0f} min)"
        )
        res.fired_signals.append("idle")
    elif idle_ratio >= config.IDLE_RATIO_WARNING:
        idle_contribution = 20.0
        res.evidence.append(
            f"Idle time {current.idle_minutes:.0f} min = {idle_ratio:.1f}x baseline ({base_idle:.0f} min)"
        )
        res.fired_signals.append("idle")
    if idle_contribution:
        res.detail.append(EvidenceDetail(
            signal="idle_minutes", kind="risk", value=float(current.idle_minutes),
            baseline=float(base_idle), ratio=round(idle_ratio, 2),
            detail=f"Idle {current.idle_minutes:.0f} min vs {base_idle:.0f} min baseline "
                   f"({idle_ratio:.1f}x, z={idle_z:.1f})",
        ))
    res.drivers["idle"] = idle_contribution

    # ---- 2. Harsh / high-load cycles ----
    harsh = _count_harsh_cycles(current, history)
    harsh_contribution = 0.0
    if harsh >= config.HARSH_CYCLES_HIGH:
        harsh_contribution = 40.0
        res.evidence.append(f"{harsh} harsh load cycles in recent window")
        res.fired_signals.append("harsh_cycles")
    elif harsh >= config.HARSH_CYCLES_WARNING:
        harsh_contribution = 22.0
        res.evidence.append(f"{harsh} harsh load cycles in recent window")
        res.fired_signals.append("harsh_cycles")
    if harsh_contribution:
        res.detail.append(EvidenceDetail(
            signal="load_cycles", kind="risk", value=float(harsh),
            baseline=float(config.HARSH_CYCLES_WARNING), ratio=None,
            detail=f"{harsh} harsh/high-load cycles in the recent window",
        ))
    res.drivers["harsh_cycles"] = harsh_contribution

    # ---- 3. Safety events ----
    safety_events = 0
    if current.safety_alert:
        safety_events += 1
    # seatbelt unfastened during a HIGH-load cycle = safety event
    if current.seatbelt == "UNFASTENED" and current.load == "HIGH":
        safety_events += 1
    safety_contribution = 0.0
    if safety_events >= config.SAFETY_EVENTS_HIGH:
        safety_contribution = 30.0 * safety_events
        res.evidence.append(
            f"{safety_events} safety event(s) detected"
            + (" (seatbelt unfastened during high load)" if current.seatbelt == "UNFASTENED" else "")
        )
        res.fired_signals.append("safety")
        res.detail.append(EvidenceDetail(
            signal="safety_event", kind="safety", value=float(safety_events),
            baseline=0.0, ratio=None,
            detail=f"{safety_events} safety event(s) in the recent window",
        ))
    res.drivers["safety"] = safety_contribution

    # ---- Combine (cap at 100) ----
    res.score = float(min(100.0, sum(res.drivers.values())))
    res.label = _label_for_score(res.score)
    return res
