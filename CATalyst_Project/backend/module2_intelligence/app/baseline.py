"""
baseline.py — establish what "normal" looks like for an operator and a machine.

Baselines are computed from the supplied history when available, otherwise we
fall back to the DEFAULT_* baselines in config.py. Everything downstream
(risk, health, confidence) compares the current reading against these numbers,
so this is the foundation of the whole module.
"""
from __future__ import annotations

from statistics import mean, pstdev
from typing import List, Dict

from .schemas import TelemetryReading
from . import config


def _safe_mean(values: List[float], fallback: float) -> float:
    return mean(values) if values else fallback


def _safe_std(values: List[float]) -> float:
    # population stdev; 0.0 when fewer than 2 points (avoids blowups)
    return pstdev(values) if len(values) >= 2 else 0.0


def operator_baseline(history: List[TelemetryReading]) -> Dict[str, float]:
    """
    Operator behavioural baseline.

    Returns mean idle_minutes and the standard deviation (for z-scores), plus
    a normal harsh-cycle rate. Falls back to config defaults if history is thin.
    """
    idle_values = [h.idle_minutes for h in history]
    base_idle = _safe_mean(idle_values, config.DEFAULT_OPERATOR_BASELINE["idle_minutes"])
    idle_std = _safe_std(idle_values)

    return {
        "idle_minutes": base_idle,
        "idle_std": idle_std,
        "load_cycles_per_hour": config.DEFAULT_OPERATOR_BASELINE["load_cycles_per_hour"],
        "_n": float(len(history)),
    }


def machine_baseline(history: List[TelemetryReading]) -> Dict[str, float]:
    """
    Machine-health baseline per signal.

    Uses only readings from a comparable/normal load where possible so a few
    high-load spikes don't inflate the 'normal' pressure. Falls back to config
    defaults when history is thin.
    """
    # Prefer non-HIGH-load readings for a clean 'normal' picture.
    calm = [h for h in history if h.load != "HIGH"] or history

    def base_for(attr: str, default: float) -> float:
        return _safe_mean([getattr(h, attr) for h in calm], default)

    def std_for(attr: str) -> float:
        return _safe_std([getattr(h, attr) for h in calm])

    d = config.DEFAULT_MACHINE_BASELINE
    return {
        "hydraulic_pressure": base_for("hydraulic_pressure", d["hydraulic_pressure"]),
        "hydraulic_pressure_std": std_for("hydraulic_pressure"),
        "vibration": base_for("vibration", d["vibration"]),
        "vibration_std": std_for("vibration"),
        "engine_temp": base_for("engine_temp", d["engine_temp"]),
        "oil_pressure": base_for("oil_pressure", d["oil_pressure"]),
        "hydraulic_temp": base_for("hydraulic_temp", d["hydraulic_temp"]),
        "rpm": base_for("rpm", d["rpm"]),
        "_n": float(len(calm)),
    }


def zscore(value: float, base: float, std: float) -> float:
    """Standard score; returns 0.0 when std is 0 (not enough history)."""
    if std <= 1e-9:
        return 0.0
    return (value - base) / std
