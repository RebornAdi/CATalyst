"""
make_sample_data.py — generate sample_data.json with three demo scenarios.

Scenarios (matching Module 1's plan):
  NORMAL            — everything within baseline
  OPERATOR_RISK     — excessive idle + harsh cycles + a safety event
  OPERATION_TO_WEAR — harsh operation AND rising hydraulic pressure/vibration
                      (the correlated pattern that fires the Link Analyzer)

Each scenario has a `current` reading and a `history` array so Module 2 can
compute real baselines. Run: python make_sample_data.py
"""
import json
import random
from datetime import datetime, timedelta

random.seed(7)

OP = "OP01"
MC = "CAT001"


def reading(ts, rpm, etemp, oilp, hydp, hydt, vib, idle, load,
            seatbelt=None, safety=None):
    r = {
        "operator_id": OP, "machine_id": MC, "timestamp": ts,
        "rpm": rpm, "engine_temp": etemp, "oil_pressure": oilp,
        "hydraulic_pressure": hydp, "hydraulic_temp": hydt,
        "vibration": vib, "idle_minutes": idle, "load": load,
    }
    if seatbelt is not None:
        r["seatbelt"] = seatbelt
    if safety is not None:
        r["safety_alert"] = safety
    return r


def normal_history(n=40, start=None):
    """A calm two-week-ish history of normal operation."""
    start = start or datetime(2026, 9, 9, 8, 0, 0)
    hist = []
    for i in range(n):
        ts = (start + timedelta(hours=i)).isoformat()
        hist.append(reading(
            ts,
            rpm=random.gauss(1800, 60),
            etemp=random.gauss(90, 2.5),
            oilp=random.gauss(4.2, 0.15),
            hydp=random.gauss(180, 8),
            hydt=random.gauss(70, 3),
            vib=random.gauss(0.35, 0.03),
            idle=max(0, random.gauss(14, 3)),
            # keep base history calm (no HIGH) so harsh-cycle counts in each
            # scenario reflect only the intentionally-added cycles
            load=random.choice(["NORMAL", "NORMAL", "LOW"]),
        ))
    return hist


def build():
    now = datetime(2026, 9, 23, 10, 30, 0)

    # ---------- NORMAL ----------
    normal_current = reading(
        now.isoformat(), rpm=1810, etemp=91, oilp=4.2,
        hydp=182, hydt=71, vib=0.34, idle=12, load="NORMAL",
        seatbelt="FASTENED", safety=False,
    )
    normal = {"current": normal_current, "history": normal_history()}

    # ---------- OPERATOR_RISK ----------
    # Recent history has several HIGH-load cycles; current shows big idle + a
    # safety event, but machine signals are still healthy (so NO correlation).
    risk_hist = normal_history(34)
    hi_start = datetime(2026, 9, 23, 6, 0, 0)
    for i in range(6):  # 6 harsh cycles in the recent window
        ts = (hi_start + timedelta(minutes=20 * i)).isoformat()
        risk_hist.append(reading(ts, rpm=1900, etemp=94, oilp=4.1,
                                 hydp=190, hydt=73, vib=0.38, idle=15, load="HIGH"))
    risk_current = reading(
        now.isoformat(), rpm=1850, etemp=95, oilp=4.1,
        hydp=188, hydt=74, vib=0.38, idle=47, load="HIGH",
        seatbelt="UNFASTENED", safety=True,
    )
    operator_risk = {"current": risk_current, "history": risk_hist}

    # ---------- OPERATION_TO_WEAR ----------
    # Harsh cycles AND rising hydraulic pressure + vibration -> correlation TRUE.
    wear_hist = normal_history(34)
    ws = datetime(2026, 9, 23, 7, 0, 0)
    # ramp: pressure and vibration climb over the last few HIGH-load readings
    for i in range(6):
        ts = (ws + timedelta(minutes=25 * i)).isoformat()
        wear_hist.append(reading(
            ts, rpm=1980, etemp=98, oilp=4.0,
            hydp=210 + i * 25,             # climbing pressure
            hydt=76 + i, vib=0.45 + i * 0.05,  # climbing vibration
            idle=16, load="HIGH",
        ))
    wear_current = reading(
        now.isoformat(), rpm=2010, etemp=101, oilp=3.9,
        hydp=430, hydt=83, vib=0.74, idle=20, load="HIGH",
        seatbelt="FASTENED", safety=False,
    )
    operation_to_wear = {"current": wear_current, "history": wear_hist}

    return {
        "NORMAL": normal,
        "OPERATOR_RISK": operator_risk,
        "OPERATION_TO_WEAR": operation_to_wear,
    }


if __name__ == "__main__":
    data = build()
    with open("sample_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("wrote sample_data.json with scenarios:", list(data.keys()))
