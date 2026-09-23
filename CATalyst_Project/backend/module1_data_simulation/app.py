from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import math
import random
from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="CATalyst Module 1 - Live Telemetry Simulator", version="2.0.0")


class Telemetry(BaseModel):
    operator_id: str
    machine_id: str
    timestamp: str
    rpm: int
    engine_temp: float
    oil_pressure: float
    hydraulic_pressure: float
    hydraulic_temp: float
    vibration: float
    idle_minutes: int
    load: str
    seatbelt: str = "FASTENED"
    safety_alert: bool = False


history: dict[str, deque[Telemetry]] = defaultdict(lambda: deque(maxlen=180))
tick = 0


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def make_telemetry(scenario: str = "normal") -> Telemetry:
    global tick
    tick += 1
    scenario = scenario.lower()
    wave = math.sin(tick / 3.0)

    if scenario == "harsh":
        # Live harsh-load stream: small temporal movement instead of isolated random rows.
        pressure = 244 + 12 * wave + random.uniform(-5, 5)
        vibration = 0.76 + 0.09 * abs(wave) + random.uniform(-0.025, 0.025)
        return Telemetry(
            operator_id="OP01", machine_id="CAT001", timestamp=now(),
            rpm=int(2250 + 70 * wave + random.randint(-25, 25)),
            engine_temp=round(94 + 3 * wave + random.uniform(-1.5, 1.5), 1),
            oil_pressure=round(4.0 + random.uniform(-0.2, 0.2), 1),
            hydraulic_pressure=round(pressure, 1),
            hydraulic_temp=round(78 + 2 * wave + random.uniform(-1, 1), 1),
            vibration=round(vibration, 2),
            idle_minutes=random.randint(35, 55), load="HIGH",
            seatbelt=random.choice(["FASTENED", "FASTENED", "UNFASTENED"]),
            safety_alert=random.choice([False, False, True]),
        )

    if scenario == "operator_risk":
        return Telemetry(
            operator_id="OP01", machine_id="CAT001", timestamp=now(),
            rpm=int(1920 + 55 * wave + random.randint(-25, 25)),
            engine_temp=round(83 + random.uniform(-3, 3), 1),
            oil_pressure=round(4.6 + random.uniform(-0.25, 0.25), 1),
            hydraulic_pressure=round(168 + random.uniform(-12, 12), 1),
            hydraulic_temp=round(67 + random.uniform(-3, 3), 1),
            vibration=round(0.35 + random.uniform(-0.06, 0.06), 2),
            idle_minutes=random.randint(38, 52), load="HIGH",
            seatbelt="UNFASTENED", safety_alert=True,
        )

    # Normal live stream oscillates around a healthy operating envelope.
    return Telemetry(
        operator_id="OP01", machine_id="CAT001", timestamp=now(),
        rpm=int(1800 + 75 * wave + random.randint(-45, 45)),
        engine_temp=round(78 + 3 * wave + random.uniform(-2, 2), 1),
        oil_pressure=round(4.8 + random.uniform(-0.25, 0.25), 1),
        hydraulic_pressure=round(110 + 8 * wave + random.uniform(-5, 5), 1),
        hydraulic_temp=round(61 + random.uniform(-3, 3), 1),
        vibration=round(0.32 + random.uniform(-0.06, 0.06), 2),
        idle_minutes=random.randint(5, 18),
        load=random.choice(["LOW", "NORMAL"]), seatbelt="FASTENED", safety_alert=False,
    )


def push(scenario: str) -> Telemetry:
    item = make_telemetry(scenario)
    history[scenario].append(item)
    return item


# Seed a baseline so the ML detector has enough context immediately.
for _ in range(80):
    push("normal")
for _ in range(80):
    push("harsh")
for _ in range(80):
    push("operator_risk")


@app.get("/")
def root():
    return {
        "module": "CATalyst Module 1 - Live Telemetry Simulator",
        "status": "ok",
        "endpoints": ["/telemetry", "/telemetry/history", "/health"],
        "scenarios": ["normal", "harsh", "operator_risk"],
        "stream": "stateful synthetic telemetry",
    }


@app.get("/health")
def health():
    return {"status": "ok", "module": "module1", "history": {k: len(v) for k, v in history.items()}}


@app.get("/telemetry", response_model=Telemetry)
def telemetry(scenario: str = "normal"):
    key = scenario.lower()
    if key not in {"normal", "harsh", "operator_risk"}:
        key = "normal"
    return push(key)


@app.get("/telemetry/history", response_model=list[Telemetry])
def telemetry_history(
    scenario: str = "normal",
    limit: int = Query(default=60, ge=1, le=180),
):
    key = scenario.lower()
    if key not in history:
        key = "normal"
    # Generate one fresh point so every poll advances the stream.
    push(key)
    return list(history[key])[-limit:]


@app.post("/telemetry", response_model=Telemetry)
def custom_telemetry(data: Telemetry):
    return data
