"""
main.py — Module 2 FastAPI service.

Endpoints
  GET  /                 -> liveness + module info
  GET  /health           -> simple health check
  POST /analyze          -> the main endpoint: telemetry in, evidence out
  GET  /demo/{scenario}  -> run a bundled scenario (NORMAL / OPERATOR_RISK /
                            OPERATION_TO_WEAR) using sample_data.json

Run:
  uvicorn app.main:app --reload --port 8002
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import AnalyzeRequest, AnalyzeResponse, TelemetryReading
from .analyzer import analyze

app = FastAPI(
    title="CATalyst Module 2 — Risk + Health + Link Analyzer",
    version="1.0.0",
    description="Computes structured evidence (risk, health, correlation, "
                "confidence) from telemetry. No LLM logic — evidence only.",
)

# Module 3/4 run on other ports/hosts during integration.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_SAMPLE_PATH = Path(__file__).resolve().parent.parent / "sample_data.json"


def _load_samples() -> dict:
    with open(_SAMPLE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/")
def root():
    return {
        "module": "CATalyst Module 2 — Risk + Health + Link Analyzer",
        "status": "ok",
        "endpoints": ["/analyze (POST)", "/demo/{scenario} (GET)", "/health (GET)"],
        "scenarios": ["NORMAL", "OPERATOR_RISK", "OPERATION_TO_WEAR"],
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(req: AnalyzeRequest) -> AnalyzeResponse:
    """
    Main endpoint. Accepts the current reading plus optional history and
    returns the frozen evidence contract for Module 3.
    """
    return analyze(req.current, req.history)


@app.get("/demo/{scenario}", response_model=AnalyzeResponse)
def demo_endpoint(scenario: str) -> AnalyzeResponse:
    """Run one of the bundled demo scenarios by name (case-insensitive)."""
    samples = _load_samples()
    key = scenario.upper()
    if key not in samples:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{scenario}'. Try one of: {list(samples.keys())}",
        )
    block = samples[key]
    current = TelemetryReading(**block["current"])
    history = [TelemetryReading(**h) for h in block.get("history", [])]
    return analyze(current, history)
