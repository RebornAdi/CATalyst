# CATalyst Integration Contract

## Service ports

| Module | Port | Main endpoint |
|---|---:|---|
| Module 1 | 8001 | `GET /telemetry?scenario=normal` |
| Module 2 | 8002 | `POST /analyze` |
| Module 3 | 8003 | `POST /copilot/scenario/harsh` |
| Module 4 | 5173 | React UI |

## End-to-end flow

```text
Module 1
  GET /telemetry
      ↓
Module 3
  collects a small recent history
      ↓
Module 2
  POST /analyze { current, history }
      ↓
Module 3
  converts evidence into operator guidance
      ↓
Module 4
  React + voice
```

Modules communicate through HTTP JSON only. They do not import each other's internal Python modules.

## Module 1 → Module 2 input

Module 2 accepts:

```json
{
  "current": {
    "operator_id": "OP01",
    "machine_id": "CAT001",
    "timestamp": "2026-09-23T10:30:00",
    "rpm": 2200,
    "engine_temp": 92,
    "oil_pressure": 4.1,
    "hydraulic_pressure": 250,
    "hydraulic_temp": 78,
    "vibration": 0.72,
    "idle_minutes": 47,
    "load": "HIGH",
    "seatbelt": "UNFASTENED",
    "safety_alert": true
  },
  "history": []
}
```

`seatbelt` and `safety_alert` are optional in Module 2, but Module 1 now emits them so the complete contract supports operator-safety evidence.

## Module 2 → Module 3 output

Frozen fields:

- `risk`
- `health`
- `correlation`
- `confidence`
- `evidence`

Additive fields include `risk_score`, `evidence_detail`, `confidence_breakdown`, and `correlation_note`.

## Module 3 → Module 4 output

```json
{
  "message": "...",
  "risk": "HIGH",
  "health": "CRITICAL",
  "confidence": 0.78,
  "action": "Start 2-minute load handling lesson",
  "evidence": ["..."],
  "correlation": true,
  "correlation_note": "..."
}
```

## Important wording

Use `simulated telemetry`, `prototype baseline`, `correlated pattern`, `evidence-backed pattern`, and `heuristic confidence`.

Do not claim live Caterpillar sensor data or proven causation.
