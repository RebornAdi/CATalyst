"""
Data contracts for Module 2.

INPUT  — matches Module 1's frozen telemetry format exactly.
OUTPUT — matches the frozen JSON contract Module 3 consumes.

Do not rename fields in TelemetryReading or AnalyzeResponse without telling
the team; these are the agreed interfaces.
"""
from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# INPUT  (Module 1 -> Module 2)
# ---------------------------------------------------------------------------
class TelemetryReading(BaseModel):
    """A single telemetry reading, exactly as Module 1 emits it."""
    operator_id: str = Field(..., examples=["OP01"])
    machine_id: str = Field(..., examples=["CAT001"])
    timestamp: str = Field(..., examples=["2026-09-23T10:30:00"])
    rpm: float
    engine_temp: float
    oil_pressure: float
    hydraulic_pressure: float
    hydraulic_temp: float
    vibration: float
    idle_minutes: float
    load: Literal["LOW", "NORMAL", "HIGH"] = "NORMAL"

    # Not in Module 1's minimal contract but sometimes available per reading.
    # Optional so we stay compatible. If present, used as a safety signal.
    seatbelt: Optional[Literal["FASTENED", "UNFASTENED"]] = None
    safety_alert: Optional[bool] = None


class AnalyzeRequest(BaseModel):
    """
    What POST /analyze accepts.

    `current` is the live reading. `history` is an optional list of recent
    readings (e.g. from Module 1's operator_history.csv) used to compute
    baselines. If history is omitted, Module 2 falls back to built-in
    baselines from config.py so it still runs standalone.
    """
    current: TelemetryReading
    history: List[TelemetryReading] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# OUTPUT  (Module 2 -> Module 3)
# ---------------------------------------------------------------------------
class EvidenceDetail(BaseModel):
    """
    Structured version of one evidence line. This is ADDITIVE — the flat
    `evidence` list of strings (the frozen contract) is still produced.
    Module 3 / the 'Explain This' UI can use these fields to render the
    trail and the confidence arithmetic without string-parsing.
    """
    signal: str                 # e.g. "hydraulic_pressure"
    kind: Literal["risk", "health", "safety"]
    value: float
    baseline: Optional[float] = None
    ratio: Optional[float] = None      # value / baseline where meaningful
    detail: str                        # the human-readable line


class ConfidenceBreakdown(BaseModel):
    """The transparent arithmetic behind the confidence score."""
    distance_term: float
    corroboration_term: float
    recency_term: float
    weights: dict
    formula: str                       # ready-to-display string


class AnalyzeResponse(BaseModel):
    """
    The FROZEN output contract for Module 3.

    The first five fields are the agreed interface and must not change:
      risk, health, correlation, confidence, evidence
    Everything after is additive and safe to ignore by a minimal consumer.
    """
    risk: Literal["LOW", "MEDIUM", "HIGH"]
    health: Literal["OK", "WARNING", "CRITICAL"]
    correlation: bool
    confidence: float                  # 0.0 .. 1.0
    evidence: List[str]                # flat, human-readable lines

    # ---- additive extras (won't break the minimal contract) ----
    risk_score: Optional[float] = None          # 0..100
    evidence_detail: Optional[List[EvidenceDetail]] = None
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    correlation_note: Optional[str] = None       # the "correlated, not causal" wording
    operator_id: Optional[str] = None
    machine_id: Optional[str] = None
    timestamp: Optional[str] = None
    ml_model: Optional[str] = None
    ml_anomaly_score: Optional[float] = None
    ml_prediction: Optional[str] = None
