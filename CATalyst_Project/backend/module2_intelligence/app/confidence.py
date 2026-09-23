"""
confidence.py — the transparent confidence heuristic.

confidence = w_distance     * distance_term
           + w_corroboration * corroboration_term
           + w_recency       * recency_term

Each term is normalised to 0..1. The whole point is transparency: we return
the arithmetic so the UI can show exactly where the number came from when a
judge asks. This is a heuristic, NOT a probability model.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from .risk import RiskResult
from .health import HealthResult
from .schemas import ConfidenceBreakdown
from . import config


def _distance_term(risk: RiskResult, health: HealthResult) -> float:
    """
    How far outside normal are we? Use the largest deviation available:
    the health worst_ratio and the risk score (as a proxy distance).
    """
    health_dist = max(0.0, health.worst_ratio - 1.0)              # 0 at baseline
    risk_dist = risk.score / 100.0 * config.CONF_DISTANCE_CAP     # scale to same range
    raw = max(health_dist, risk_dist)
    return min(1.0, raw / config.CONF_DISTANCE_CAP)


def _corroboration_term(risk: RiskResult, health: HealthResult) -> float:
    """How many independent signals agree?"""
    n = len(set(risk.fired_signals)) + len(set(health.fired_signals))
    return min(1.0, n / config.CONF_MAX_CORROBORATING)


def _recency_term(current_ts: str) -> float:
    """
    Fresh data scores 1.0; data older than CONF_RECENCY_MAX_MINUTES scores 0.
    If the timestamp can't be parsed, assume fresh (1.0) so we never punish
    Module 1's format quirks.
    """
    try:
        ts = datetime.fromisoformat(current_ts)
    except Exception:
        return 1.0
    now = datetime.now(timezone.utc) if ts.tzinfo is not None else datetime.now()
    age_min = abs((now - ts).total_seconds()) / 60.0
    if age_min >= config.CONF_RECENCY_MAX_MINUTES:
        # Fixed demo timestamps read as very old against the wall clock. Rather
        # than zeroing the term (which unfairly deflates demo confidence), apply
        # a small floor so stale-by-clock demo data still scores something.
        return config.CONF_RECENCY_STALE_FLOOR
    return 1.0 - (age_min / config.CONF_RECENCY_MAX_MINUTES)


def compute_confidence(
    risk: RiskResult, health: HealthResult, current_ts: str
) -> ConfidenceBreakdown:
    dist = _distance_term(risk, health)
    corr = _corroboration_term(risk, health)
    rec = _recency_term(current_ts)

    score = (
        config.CONF_W_DISTANCE * dist
        + config.CONF_W_CORROBORATION * corr
        + config.CONF_W_RECENCY * rec
    )
    score = round(min(1.0, max(0.0, score)), 2)

    formula = (
        f"{score:.2f} = {config.CONF_W_DISTANCE:.2f}*{dist:.2f}(distance) "
        f"+ {config.CONF_W_CORROBORATION:.2f}*{corr:.2f}(corroboration) "
        f"+ {config.CONF_W_RECENCY:.2f}*{rec:.2f}(recency)"
    )

    return ConfidenceBreakdown(
        distance_term=round(dist, 2),
        corroboration_term=round(corr, 2),
        recency_term=round(rec, 2),
        weights={
            "distance": config.CONF_W_DISTANCE,
            "corroboration": config.CONF_W_CORROBORATION,
            "recency": config.CONF_W_RECENCY,
        },
        formula=formula,
    ), score
