# CATalyst — Module 2: Risk + Machine Health + Link Analyzer

**Owner: Person 2** · Caterpillar Hackathon 2026

The analytical brain of CATalyst. It takes telemetry (from Module 1) and
produces **structured evidence** — an operator risk level, a machine health
status, whether the two are correlated in the same time window, a transparent
confidence score, and human-readable evidence lines.

> **Evidence first, language second.** This module computes the numbers. It
> contains **no LLM logic** — Module 3 explains the evidence this module returns.
> Correlation is reported as a **correlated / evidence-backed pattern, never as
> proven causation.**

---

## Quick start

```bash
# 1. (optional) create a virtualenv
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. install
pip install -r requirements.txt

# 3. generate the demo data (writes sample_data.json)
python make_sample_data.py

# 4a. run the test suite (one command, proves it works offline)
python -m tests.test_scenarios

# 4b. OR start the API
uvicorn app.main:app --reload --port 8002
```

Then open <http://127.0.0.1:8002/docs> for interactive Swagger docs.

---

## The one command to test everything

```bash
python -m tests.test_scenarios
```

Runs all three demo scenarios through the full pipeline and asserts the
verdicts and the output contract. Exits non-zero on any failure.

---

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Module info + liveness |
| GET | `/health` | Health check |
| POST | `/analyze` | **Main endpoint** — telemetry in, evidence out |
| GET | `/demo/{scenario}` | Run a bundled scenario: `NORMAL`, `OPERATOR_RISK`, `OPERATION_TO_WEAR` |

### `POST /analyze`

**Request** — the current reading plus an *optional* `history` array (used for
baselines; if omitted, built-in baselines from `app/config.py` are used, so the
module still runs standalone):

```json
{
  "current": {
    "operator_id": "OP01", "machine_id": "CAT001",
    "timestamp": "2026-09-23T10:30:00",
    "rpm": 2010, "engine_temp": 101, "oil_pressure": 3.9,
    "hydraulic_pressure": 430, "hydraulic_temp": 83,
    "vibration": 0.74, "idle_minutes": 20, "load": "HIGH"
  },
  "history": []
}
```

**Response** — the **frozen contract** (first five fields) plus additive extras:

```json
{
  "risk": "MEDIUM",
  "health": "CRITICAL",
  "correlation": true,
  "confidence": 0.56,
  "evidence": [
    "7 harsh load cycles in recent window",
    "Hydraulic pressure 430.00 = 2.4x baseline (179)",
    "Vibration 0.74 = 2.1x baseline (0.35)",
    "Correlated in this window: ..."
  ],
  "risk_score": 40.0,
  "evidence_detail": [ ... ],
  "confidence_breakdown": {
    "distance_term": 0.47, "corroboration_term": 0.75, "recency_term": 0.5,
    "weights": {"distance": 0.4, "corroboration": 0.3, "recency": 0.3},
    "formula": "0.56 = 0.40*0.47(distance) + 0.30*0.75(corroboration) + 0.30*0.50(recency)"
  },
  "correlation_note": "Operator behaviour and machine wear are moving together ... not proven causation."
}
```

> **For Module 3 / Module 4:** the five frozen fields — `risk`, `health`,
> `correlation`, `confidence`, `evidence` — will not change. Everything after
> them (`risk_score`, `evidence_detail`, `confidence_breakdown`,
> `correlation_note`) is **additive** and safe to ignore, but powers the
> "Explain This" UI and the confidence arithmetic if you want it.

---

## The frozen output contract

```json
{
  "risk": "HIGH",            // LOW | MEDIUM | HIGH
  "health": "WARNING",       // OK | WARNING | CRITICAL
  "correlation": true,
  "confidence": 0.91,        // 0.0 .. 1.0
  "evidence": ["6 harsh load cycles", "Hydraulic pressure 2.4x baseline", "..."]
}
```

---

## Demo scenarios (tested)

| Scenario | Expected risk | Expected health | Correlation | What it shows |
| --- | --- | --- | --- | --- |
| `NORMAL` | LOW | OK | false | Everything within baseline |
| `OPERATOR_RISK` | HIGH | OK | false | Risky driving, healthy machine (idle 3.3×, 7 harsh cycles, seatbelt event) |
| `OPERATION_TO_WEAR` | MEDIUM+ | CRITICAL | **true** | Harsh operation **and** rising hydraulic pressure + vibration — the wow moment |

Try them live:

```bash
curl http://127.0.0.1:8002/demo/NORMAL
curl http://127.0.0.1:8002/demo/OPERATOR_RISK
curl http://127.0.0.1:8002/demo/OPERATION_TO_WEAR
```

---

## How it works (pipeline)

```
telemetry ─► baseline.py ─► risk.py ──┐
                        └► health.py ─┼► link_analyzer.py ─► confidence.py ─► response
                                      │
                        (evidence computed first; no LLM anywhere)
```

- **baseline.py** — operator + machine baselines from history (or config fallbacks).
- **risk.py** — idle ratio, harsh-cycle count, safety events → 0–100 risk score → LOW/MEDIUM/HIGH.
- **health.py** — hydraulic/vibration drift (ratio), engine-temp ceiling, oil-pressure floor → OK/WARNING/CRITICAL. Isolation Forest is an optional stretch overlay (auto-skips if scikit-learn absent).
- **link_analyzer.py** — correlation is TRUE only when risk ≥ MEDIUM **and** health ≥ WARNING in the same window.
- **confidence.py** — transparent heuristic: `0.40·distance + 0.30·corroboration + 0.30·recency`, with the arithmetic returned for display.

All thresholds live in **`app/config.py`** — tune there, nothing else changes.

---

## Definition of done ✔

- [x] Runs on a fresh environment (`pip install -r requirements.txt`)
- [x] Works on the agreed sample input
- [x] Produces the agreed output format (frozen contract)
- [x] Three realistic scenarios tested (`python -m tests.test_scenarios`)
- [x] README complete enough for a teammate to run it
- [x] Connectable to the final system without rewriting core logic

---

## Notes for integration

- Module 2 owns **analytical evidence only**. No language, no routing.
- Module 3 posts telemetry to `/analyze` and explains the returned evidence.
- Keep field names stable; tell the team before changing the frozen five.
- To enable the Isolation Forest stretch: uncomment `scikit-learn` and `numpy`
  in `requirements.txt`; it activates automatically when ≥30 history points exist.
