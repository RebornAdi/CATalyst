"""Small, deterministic ML anomaly detector used by CATalyst.

The model learns the normal operating envelope from synthetic baseline data and
returns an anomaly score for each live sensor vector. This is intentionally an
unsupervised model: no hand-written risk label is fed into the model.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

FEATURES = [
    "rpm", "engine_temp", "oil_pressure", "hydraulic_pressure",
    "hydraulic_temp", "vibration", "idle_minutes",
]


def _normal_training_data(n: int = 600, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.column_stack([
        rng.normal(1800, 90, n),
        rng.normal(78, 4, n),
        rng.normal(4.8, 0.25, n),
        rng.normal(110, 12, n),
        rng.normal(61, 4, n),
        rng.normal(0.32, 0.06, n),
        rng.uniform(4, 20, n),
    ])


MODEL = IsolationForest(
    n_estimators=180,
    contamination=0.06,
    random_state=42,
    n_jobs=-1,
)
MODEL.fit(_normal_training_data())


def predict(reading) -> dict:
    vector = np.array([[float(getattr(reading, f)) for f in FEATURES]])
    raw = float(MODEL.decision_function(vector)[0])
    # Convert the signed Isolation Forest score into a readable 0..1 anomaly score.
    score = max(0.0, min(1.0, 0.5 - raw))
    label = "ANOMALOUS" if score >= 0.50 else "NORMAL"
    return {
        "model": "IsolationForest",
        "anomaly_score": round(score, 3),
        "prediction": label,
        "features": FEATURES,
    }
