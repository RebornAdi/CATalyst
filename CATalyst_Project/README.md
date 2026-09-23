# CATalyst — Caterpillar Hackathon 2026

CATalyst is a prototype AI Operator Co-Pilot that connects operator behaviour with simulated machine telemetry and turns evidence into practical, explainable guidance.

## Architecture

```text
Module 1: Machine Data & Simulation (:8001)
              |
              | telemetry + recent history
              v
Module 2: Risk + Machine Health + Link Analyzer (:8002)
              |
              | structured evidence
              v
Module 3: AI Orchestrator + Scheduler + Coach (:8003)
              |
              | operator response
              v
Module 4: React Operator App + Voice (:5173)
```

The modules communicate through HTTP JSON contracts. No module imports another module's internal Python code.

## Important prototype wording

The machine telemetry is **simulated telemetry**. It demonstrates how a real telemetry stream could be processed; it does not claim to use live Caterpillar machine sensor data.

The Link Analyzer reports a **correlated/evidence-backed pattern**, not proven causation.

Confidence is a transparent heuristic, not a statistically validated probability.

## Requirements

- Python 3.11+ (3.13 is also expected to work with the pinned ranges)
- Node.js 18+
- npm

## Fastest setup — one project environment

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cd frontend
npm install
cd ..
```

Then run everything at once:

```bash
./run_all.sh
```

Open:

- Frontend: http://127.0.0.1:5173
- Module 1: http://127.0.0.1:8001/docs
- Module 2: http://127.0.0.1:8002/docs
- Module 3: http://127.0.0.1:8003/docs

Press `Ctrl+C` in the `run_all.sh` terminal to stop all services.

## Run modules individually

### Module 1

```bash
cd backend/module1_data_simulation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8001
```

### Module 2

```bash
cd backend/module2_intelligence
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

### Module 3

```bash
cd backend/module3_orchestrator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8003
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Tests

After the root `.venv` is set up:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m tests.test_scenarios
```

The first command checks cross-module contracts. The second runs Module 2's three bundled scenarios.

## End-to-end API test

With all three backends running:

```bash
curl http://127.0.0.1:8001/telemetry
curl http://127.0.0.1:8002/demo/NORMAL
curl -X POST http://127.0.0.1:8003/copilot/scenario/normal
curl -X POST http://127.0.0.1:8003/copilot/scenario/harsh
```

The last command is the main end-to-end path:

```text
Module 3 -> Module 1 telemetry -> recent history -> Module 2 -> Module 3 response
```

## Frontend demo

1. Open the frontend.
2. Click **Simulate normal**.
3. Click **Simulate harsh operation**.
4. Ask **Why was I flagged?**.
5. Ask **Is my machine okay?**.
6. Show the evidence trail.
7. Use **Talk to CATalyst** if browser speech recognition is supported.

The frontend can also run without the backend by creating `frontend/.env`:

```env
VITE_MODULE3_URL=http://127.0.0.1:8003
VITE_USE_MOCK=true
```

Restart Vite after changing environment variables.

## Service contracts

### Module 1 → Module 2

Module 1 emits a telemetry reading. Module 2's `/analyze` accepts:

```json
{
  "current": { "operator_id": "OP01", "machine_id": "CAT001", "timestamp": "2026-09-23T10:30:00", "rpm": 2200, "engine_temp": 92, "oil_pressure": 4.1, "hydraulic_pressure": 250, "hydraulic_temp": 78, "vibration": 0.72, "idle_minutes": 47, "load": "HIGH", "seatbelt": "UNFASTENED", "safety_alert": true },
  "history": []
}
```

`seatbelt` and `safety_alert` are optional in Module 2 but are emitted by Module 1 to support safety evidence.

### Module 2 → Module 3

Frozen fields:

```json
{
  "risk": "HIGH",
  "health": "WARNING",
  "correlation": true,
  "confidence": 0.91,
  "evidence": ["..."]
}
```

Module 2 also returns additive evidence and confidence details.

### Module 3 → Module 4

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

## Troubleshooting

### `GET /` returns 404

If a service does not define `/`, use `/health` or `/docs`. The current integrated project defines root routes for all backend services.

### `ModuleNotFoundError: fastapi`

Do not use the Anaconda base environment for the project. From the root:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Then use `.venv/bin/python` and `.venv/bin/uvicorn`.

### Frontend says backend unavailable

Make sure Modules 1, 2 and 3 are running. Check:

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:8003/health
```

## Team ownership

- Person 1: `backend/module1_data_simulation`
- Person 2: `backend/module2_intelligence`
- Person 3: `backend/module3_orchestrator`
- Person 4: `frontend`

Each module remains independently runnable, while `run_all.sh` provides a one-command local demo.

## Voice-command flow

The React voice input uses the browser Speech Recognition API. The resulting transcript is sent to Module 3 as the `question` query parameter:

```text
Browser microphone
    -> SpeechRecognition transcript
    -> Module 4 App.jsx
    -> POST /copilot/scenario/{scenario}?question=...
    -> Module 3 intent router
    -> Module 1 telemetry + Module 2 evidence
    -> question-specific operator response
```

Module 3 uses a deterministic offline intent router for the MVP. It distinguishes explanation/"why", machine health, operator status, and next-step/shift questions. The response also includes the detected `intent` and original `question` as additive fields for debugging.

For a local setup on Windows, recreate the Python environment and install frontend dependencies rather than using a copied `.venv` or `node_modules` directory:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-dev.txt
cd frontend
npm install
npm run dev
```

## Live telemetry + ML layer

The current build includes a **stateful synthetic telemetry stream**. Module 1 keeps a rolling history for Normal, Operation → Wear and Operator Risk scenarios and exposes:

```text
GET /telemetry
GET /telemetry/history?scenario=normal&limit=60
```

Module 3 exposes the integrated live endpoint used by the dashboard:

```text
GET /live/scenario/OPERATION_TO_WEAR
```

The React dashboard polls this endpoint automatically and updates machine metrics and trend charts without requiring a new voice question.

### ML model

Module 2 now runs an **Isolation Forest** anomaly detector on every live sensor vector. The model learns a normal operating envelope from synthetic baseline telemetry and returns:

- `ml_model`
- `ml_anomaly_score` (0–1)
- `ml_prediction` (`NORMAL` / `ANOMALOUS`)

The ML result is an additional evidence signal; the deterministic safety/health thresholds remain visible so the demo is explainable.

### Dashboard buttons

The left rail is now functional:

- Dashboard — live Co-Pilot + voice
- Maintenance — maintenance/evidence view
- Settings — endpoint, scenario and stream controls
- Analytics — live telemetry trend charts
- Help — operator guide
- Exit — demo exit dialog

### Windows one-command start

From PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run_all.ps1
```
