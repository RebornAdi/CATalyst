"""
test_scenarios.py — verify Module 2 on the three demo scenarios.

Run from the project root:  python -m tests.test_scenarios
Exits non-zero if any assertion fails, so it doubles as a CI smoke test.
"""
import json
import sys
from pathlib import Path

from app.schemas import TelemetryReading
from app.analyzer import analyze

ROOT = Path(__file__).resolve().parent.parent


def load():
    with open(ROOT / "sample_data.json", encoding="utf-8") as f:
        return json.load(f)


def run_scenario(name, block):
    current = TelemetryReading(**block["current"])
    history = [TelemetryReading(**h) for h in block.get("history", [])]
    return analyze(current, history)


def check(cond, msg):
    cond = bool(cond)
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {msg}")
    return cond


def main():
    data = load()
    all_ok = True

    # ---- frozen contract shape on every scenario ----
    print("Contract shape:")
    for name, block in data.items():
        resp = run_scenario(name, block)
        d = resp.model_dump()
        for field in ("risk", "health", "correlation", "confidence", "evidence"):
            all_ok &= check(field in d, f"{name}: has '{field}'")
        all_ok &= check(d["risk"] in ("LOW", "MEDIUM", "HIGH"), f"{name}: risk label valid")
        all_ok &= check(d["health"] in ("OK", "WARNING", "CRITICAL"), f"{name}: health label valid")
        all_ok &= check(0.0 <= d["confidence"] <= 1.0, f"{name}: confidence in [0,1]")
        all_ok &= check(isinstance(d["evidence"], list) and d["evidence"], f"{name}: evidence non-empty")

    # ---- semantic expectations per scenario ----
    print("\nNORMAL expectations:")
    r = run_scenario("NORMAL", data["NORMAL"])
    all_ok &= check(r.risk == "LOW", f"risk is LOW (got {r.risk})")
    all_ok &= check(r.health == "OK", f"health is OK (got {r.health})")
    all_ok &= check(r.correlation is False, "no correlation")

    print("\nOPERATOR_RISK expectations:")
    r = run_scenario("OPERATOR_RISK", data["OPERATOR_RISK"])
    all_ok &= check(r.risk in ("MEDIUM", "HIGH"), f"risk elevated (got {r.risk})")
    all_ok &= check(r.health == "OK", f"machine still healthy (got {r.health})")
    all_ok &= check(r.correlation is False, "no correlation (risk without wear)")
    all_ok &= check(any("idle" in e.lower() for e in r.evidence), "idle evidence present")
    all_ok &= check(any("safety" in e.lower() for e in r.evidence), "safety evidence present")

    print("\nOPERATION_TO_WEAR expectations:")
    r = run_scenario("OPERATION_TO_WEAR", data["OPERATION_TO_WEAR"])
    all_ok &= check(r.risk in ("MEDIUM", "HIGH"), f"risk elevated (got {r.risk})")
    all_ok &= check(r.health in ("WARNING", "CRITICAL"), f"health degraded (got {r.health})")
    all_ok &= check(r.correlation is True, "correlation TRUE (the wow moment)")
    all_ok &= check(any("hydraulic" in e.lower() for e in r.evidence), "hydraulic evidence present")
    all_ok &= check(r.correlation_note and "not proven causation" in r.correlation_note.lower(),
                    "correlation note disclaims causation")
    all_ok &= check(r.confidence_breakdown is not None, "confidence breakdown present")
    print("  confidence formula:", r.confidence_breakdown.formula)

    print("\n" + ("ALL TESTS PASSED" if all_ok else "SOME TESTS FAILED"))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
