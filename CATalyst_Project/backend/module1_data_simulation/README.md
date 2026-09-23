# CATalyst Module 1 — Machine Data & Simulation

Simulates machine telemetry for the CATalyst prototype. The values are synthetic and are not live Caterpillar sensor data.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8001
```

Open `http://127.0.0.1:8001/docs`.

## Scenarios

```bash
curl "http://127.0.0.1:8001/telemetry?scenario=normal"
curl "http://127.0.0.1:8001/telemetry?scenario=harsh"
curl "http://127.0.0.1:8001/telemetry?scenario=operator_risk"
```
