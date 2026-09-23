"""
analyzer.py — the single entry point that runs the whole Module 2 pipeline
and assembles the frozen output contract.

Pipeline: baselines -> risk -> health -> link -> confidence -> response.
This is pure computation and can be called directly (no HTTP needed), which
makes it easy to unit-test and to reuse from main.py.
"""
from __future__ import annotations

from typing import List

from .schemas import (
    TelemetryReading, AnalyzeResponse, EvidenceDetail,
)
from .baseline import operator_baseline, machine_baseline
from .risk import evaluate_risk
from .health import evaluate_health
from .link_analyzer import analyze_link
from .confidence import compute_confidence


def analyze(current: TelemetryReading, history: List[TelemetryReading]) -> AnalyzeResponse:
    # 1. Baselines (from history, or config fallbacks)
    op_base = operator_baseline(history)
    mac_base = machine_baseline(history)

    # 2. Evidence
    risk = evaluate_risk(current, history, op_base)
    health = evaluate_health(current, history, mac_base)

    # 3. Link (operation-to-wear)
    link = analyze_link(risk, health)

    # 4. Confidence (transparent)
    breakdown, conf_score = compute_confidence(risk, health, current.timestamp)

    # 5. Assemble flat evidence list (the frozen contract) ...
    evidence: List[str] = []
    evidence.extend(risk.evidence)
    evidence.extend(health.evidence)
    evidence.extend(link.evidence)
    if not evidence:
        evidence.append("All signals within normal range")

    # ... and the structured detail (additive)
    detail: List[EvidenceDetail] = []
    detail.extend(risk.detail)
    detail.extend(health.detail)

    return AnalyzeResponse(
        # --- frozen five ---
        risk=risk.label,
        health=health.status,
        correlation=link.correlation,
        confidence=conf_score,
        evidence=evidence,
        # --- additive extras ---
        risk_score=risk.score,
        evidence_detail=detail or None,
        confidence_breakdown=breakdown,
        correlation_note=link.note or None,
        operator_id=current.operator_id,
        machine_id=current.machine_id,
        timestamp=current.timestamp,
        ml_model=health.ml_model,
        ml_anomaly_score=health.ml_anomaly_score,
        ml_prediction=health.ml_prediction,
    )
