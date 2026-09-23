"""
health.py — evaluate MACHINE condition from sensor signals.

Primary method (now): threshold + ratio drift against the machine baseline for
hydraulic pressure, vibration, engine temp and oil pressure.

Stretch method (stubbed): Isolation Forest anomaly detection over the sensor
vector. Enabled only if scikit-learn is installed AND enough history exists;
otherwise we silently use thresholds. This keeps the module dependency-light
and always runnable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional

from .schemas import TelemetryReading, EvidenceDetail
from . import config


@dataclass
class HealthResult:
    status: str                      # OK / WARNING / CRITICAL
    evidence: List[str] = field(default_factory=list)
    detail: List[EvidenceDetail] = field(default_factory=list)
    fired_signals: List[str] = field(default_factory=list)
    worst_ratio: float = 1.0         # largest drift ratio seen (for confidence)
    ml_model: str = "IsolationForest"
    ml_anomaly_score: float = 0.0
    ml_prediction: str = "NORMAL"


def _escalate(current: str, candidate: str) -> str:
    """Return the more severe of two statuses."""
    order = config.HEALTH_STATUSES  # ["OK","WARNING","CRITICAL"]
    return candidate if order.index(candidate) > order.index(current) else current


def _check_ratio(
    res: HealthResult, signal: str, value: float, base: float,
    warn: float, crit: float,
) -> None:
    """Ratio-based drift check (value climbing above baseline)."""
    if base <= 1e-9:
        return
    ratio = value / base
    base_str = f"{base:.2f}" if base < 10 else f"{base:.0f}"
    if ratio >= crit:
        res.status = _escalate(res.status, "CRITICAL")
        res.evidence.append(f"{_pretty(signal)} {value:.2f} = {ratio:.1f}x baseline ({base_str})")
        res.fired_signals.append(signal)
    elif ratio >= warn:
        res.status = _escalate(res.status, "WARNING")
        res.evidence.append(f"{_pretty(signal)} {value:.2f} = {ratio:.1f}x baseline ({base_str})")
        res.fired_signals.append(signal)
    if ratio >= warn:
        res.worst_ratio = max(res.worst_ratio, ratio)
        res.detail.append(EvidenceDetail(
            signal=signal, kind="health", value=round(value, 2),
            baseline=round(base, 2), ratio=round(ratio, 2),
            detail=f"{_pretty(signal)} {value:.1f} vs {base:.0f} baseline ({ratio:.1f}x)",
        ))


def _check_ceiling(
    res: HealthResult, signal: str, value: float, warn: float, crit: float,
) -> None:
    """Absolute-ceiling check (e.g. engine temp too high)."""
    if value >= crit:
        res.status = _escalate(res.status, "CRITICAL")
        res.evidence.append(f"{_pretty(signal)} {value:.0f} above critical ceiling ({crit:.0f})")
        res.fired_signals.append(signal)
        res.detail.append(EvidenceDetail(signal=signal, kind="health", value=round(value, 2),
                                         baseline=crit, ratio=None,
                                         detail=f"{_pretty(signal)} {value:.0f} >= critical {crit:.0f}"))
    elif value >= warn:
        res.status = _escalate(res.status, "WARNING")
        res.evidence.append(f"{_pretty(signal)} {value:.0f} above warning ceiling ({warn:.0f})")
        res.fired_signals.append(signal)
        res.detail.append(EvidenceDetail(signal=signal, kind="health", value=round(value, 2),
                                         baseline=warn, ratio=None,
                                         detail=f"{_pretty(signal)} {value:.0f} >= warning {warn:.0f}"))


def _check_floor(
    res: HealthResult, signal: str, value: float, warn: float, crit: float,
) -> None:
    """Absolute-floor check (e.g. oil pressure too low)."""
    if value <= crit:
        res.status = _escalate(res.status, "CRITICAL")
        res.evidence.append(f"{_pretty(signal)} {value:.1f} below critical floor ({crit:.1f})")
        res.fired_signals.append(signal)
        res.detail.append(EvidenceDetail(signal=signal, kind="health", value=round(value, 2),
                                         baseline=crit, ratio=None,
                                         detail=f"{_pretty(signal)} {value:.1f} <= critical {crit:.1f}"))
    elif value <= warn:
        res.status = _escalate(res.status, "WARNING")
        res.evidence.append(f"{_pretty(signal)} {value:.1f} below warning floor ({warn:.1f})")
        res.fired_signals.append(signal)
        res.detail.append(EvidenceDetail(signal=signal, kind="health", value=round(value, 2),
                                         baseline=warn, ratio=None,
                                         detail=f"{_pretty(signal)} {value:.1f} <= warning {warn:.1f}"))


def _pretty(signal: str) -> str:
    return signal.replace("_", " ").capitalize()


def evaluate_health(
    current: TelemetryReading,
    history: List[TelemetryReading],
    mac_base: Dict[str, float],
) -> HealthResult:
    res = HealthResult(status="OK")

    # Ratio-based drift
    _check_ratio(res, "hydraulic_pressure", current.hydraulic_pressure,
                 mac_base["hydraulic_pressure"],
                 config.HYDRAULIC_RATIO_WARNING, config.HYDRAULIC_RATIO_CRITICAL)
    _check_ratio(res, "vibration", current.vibration, mac_base["vibration"],
                 config.VIBRATION_RATIO_WARNING, config.VIBRATION_RATIO_CRITICAL)

    # Absolute ceilings / floors
    _check_ceiling(res, "engine_temp", current.engine_temp,
                   config.ENGINE_TEMP_WARNING, config.ENGINE_TEMP_CRITICAL)
    _check_floor(res, "oil_pressure", current.oil_pressure,
                 config.OIL_PRESSURE_LOW_WARNING, config.OIL_PRESSURE_LOW_CRITICAL)

    # ML layer: a learned normal-envelope model runs on every reading.
    try:
        from .ml_model import predict
        ml = predict(current)
        res.ml_model = ml["model"]
        res.ml_anomaly_score = ml["anomaly_score"]
        res.ml_prediction = ml["prediction"]
        if res.ml_prediction == "ANOMALOUS" and res.ml_anomaly_score >= 0.62:
            res.status = _escalate(res.status, "WARNING")
            res.evidence.append(
                f"ML anomaly detector score {res.ml_anomaly_score:.2f} indicates an unusual multivariate pattern"
            )
            res.fired_signals.append("ml_anomaly")
            res.detail.append(EvidenceDetail(
                signal="ml_anomaly", kind="health", value=round(res.ml_anomaly_score, 3),
                baseline=0.0, ratio=None,
                detail=f"Isolation Forest anomaly score {res.ml_anomaly_score:.2f}",
            ))
    except Exception:
        # Threshold analysis remains available if an optional runtime dependency fails.
        pass

    return res
