# CATalyst Module 3 — AI Orchestrator + Scheduler + Coach

Module 3 consumes Module 2's evidence over HTTP and turns it into operator-facing guidance. It also provides an end-to-end scenario endpoint that pulls simulated telemetry from Module 1 first.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8003
```

Open `http://127.0.0.1:8003/docs`.

## End-to-end scenario

```bash
curl -X POST "http://127.0.0.1:8003/copilot/scenario/normal"
curl -X POST "http://127.0.0.1:8003/copilot/scenario/harsh"
curl -X POST "http://127.0.0.1:8003/copilot/scenario/operator_risk"
```

Module 3 calls Module 1, builds a small recent history, sends `{current, history}` to Module 2, and converts the evidence into an explainable response.
