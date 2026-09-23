import os
from typing import List

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(
    title="CATalyst Module 3 - AI Orchestrator",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODULE1_URL = os.getenv("MODULE1_URL", "http://127.0.0.1:8001").rstrip("/")
MODULE2_URL = os.getenv("MODULE2_URL", "http://127.0.0.1:8002").rstrip("/")


class Telemetry(BaseModel):
    operator_id: str
    machine_id: str
    timestamp: str
    rpm: float
    engine_temp: float
    oil_pressure: float
    hydraulic_pressure: float
    hydraulic_temp: float
    vibration: float
    idle_minutes: float
    load: str
    seatbelt: str = "FASTENED"
    safety_alert: bool = False


class Analysis(BaseModel):
    risk: str
    health: str
    correlation: bool
    confidence: float
    evidence: List[str]
    risk_score: float | None = None
    evidence_detail: list | None = None
    confidence_breakdown: dict | None = None
    correlation_note: str | None = None
    operator_id: str | None = None
    machine_id: str | None = None
    timestamp: str | None = None
    ml_model: str | None = None
    ml_anomaly_score: float | None = None
    ml_prediction: str | None = None


class CopilotResponse(BaseModel):
    message: str
    risk: str
    health: str
    confidence: float
    action: str
    evidence: List[str]
    correlation: bool = False
    correlation_note: str | None = None
    risk_score: float | None = None
    evidence_detail: list | None = None
    # Additive fields. Existing frontend/contract consumers can ignore them.
    intent: str = "status"
    question: str | None = None
    ml_model: str | None = None
    ml_anomaly_score: float | None = None
    ml_prediction: str | None = None


class LiveResponse(BaseModel):
    telemetry: Telemetry
    analysis: Analysis


def normalize_question(question: str | None) -> str:
    if not question:
        return ""
    return " ".join(question.strip().lower().split())


def detect_intent(question: str | None) -> str:
    """Deterministic natural-language routing for the current MVP.

    The important point is that the operator's transcript is used here. This
    is not pretending to be an LLM; it is a transparent fallback router that
    works offline and can later be replaced by an LLM adapter.
    """
    q = normalize_question(question)
    if not q:
        return "status"

    # Put highly specific phrases before broad words such as "why".
    if any(
        p in q
        for p in (
            "rest of my day",
            "rest of the day",
            "rest of my shift",
            "rest of the shift",
            "what should i do next",
            "what do i do next",
            "what should i do now",
            "what should i focus on",
            "what should i do",
            "what do you recommend",
            "next task",
            "next shift",
        )
    ):
        return "day"

    if any(
        p in q
        for p in (
            "how am i doing",
            "how did i do",
            "how is my performance",
            "how was my performance",
            "my performance",
            "my operator risk",
            "operator risk",
            "operator status",
            "am i doing okay",
            "am i doing ok",
            "am i operating safely",
            "am i safe",
            "am i operating well",
            "how safe am i",
        )
    ):
        return "operator"

    if any(
        p in q
        for p in (
            "is my machine okay",
            "is my machine ok",
            "is the machine okay",
            "is the machine ok",
            "machine health",
            "machine status",
            "machine condition",
            "what is wrong with the machine",
            "what's wrong with the machine",
            "what is wrong with my machine",
            "what's wrong with my machine",
            "is the excavator okay",
            "is the excavator ok",
            "what is wrong with the excavator",
            "what's wrong with the excavator",
        )
    ):
        return "machine"

    if any(
        p in q
        for p in (
            "why",
            "reason",
            "explain",
            "evidence",
            "what caused",
            "what triggered",
            "why was i",
            "why am i",
            "why did you",
            "what is the reason",
            "how did you decide",
        )
    ):
        return "why"

    # General machine terms are checked after the WHY route so a question
    # such as "Why is hydraulic pressure high?" is treated as an explanation
    # request rather than a generic machine-health request.
    if any(
        p in q
        for p in (
            "hydraulic",
            "hydraulics",
            "vibration",
            "engine",
            "oil pressure",
            "temperature",
            "excavator",
            "machine",
        )
    ):
        return "machine"

    return "status"


def _evidence_for_machine(analysis: Analysis) -> list[str]:
    machine_keywords = (
        "hydraulic",
        "vibration",
        "engine",
        "oil",
        "temperature",
        "machine",
        "isolation",
    )
    return [
        item
        for item in analysis.evidence
        if any(word in item.lower() for word in machine_keywords)
    ]


def build_response(
    analysis: Analysis,
    intent: str = "status",
    question: str | None = None,
) -> CopilotResponse:
    """Turn Module 2 evidence into an answer for the actual operator intent.

    Intent-specific branches intentionally happen BEFORE the generic
    correlation/health branch. Otherwise OPERATION_TO_WEAR would produce the
    same generic message for every question.
    """
    intent = (intent or "status").lower()
    evidence = analysis.evidence or []

    if intent == "why":
        if evidence:
            message = (
                "I flagged this because "
                + "; ".join(evidence[:4])
                + "."
            )
        else:
            message = (
                "I flagged this because the current telemetry differs "
                "from the prototype baseline."
            )
        action = "Review the evidence details"

    elif intent == "machine":
        machine_evidence = _evidence_for_machine(analysis)
        selected = machine_evidence or evidence

        if analysis.health == "OK":
            message = (
                "The machine is currently within the prototype health "
                "baseline. No critical machine signal was detected."
            )
            action = "Continue monitoring the machine"
        elif analysis.health == "WARNING":
            message = (
                "The machine is showing warning-level signals. "
                "The main evidence is "
                + ("; ".join(selected[:3]) if selected else "an elevated telemetry signal")
                + "."
            )
            action = "Review machine evidence before the next high-load task"
        else:
            message = (
                "The machine is showing critical signals. "
                "The main evidence is "
                + ("; ".join(selected[:3]) if selected else "multiple elevated telemetry signals")
                + "."
            )
            action = "Review machine evidence before the next high-load task"

    elif intent == "operator":
        confidence = round(analysis.confidence * 100)

        if analysis.risk == "LOW":
            message = (
                f"Your current operating risk is LOW with {confidence}% "
                "evidence confidence. Your operating pattern is within "
                "the prototype baseline."
            )
            action = "Continue current operation"
        elif analysis.risk == "MEDIUM":
            message = (
                f"Your current operating risk is MEDIUM with {confidence}% "
                "evidence confidence. Some operating signals are elevated "
                "compared with the prototype baseline."
            )
            action = "Review operator coaching"
        else:
            message = (
                f"Your current operating risk is HIGH with {confidence}% "
                "evidence confidence. Several operating signals are elevated "
                "compared with the prototype baseline."
            )
            action = "Review operator coaching before the next high-load task"

    elif intent == "day":
        message = (
            "For the rest of your shift, keep load changes smooth, avoid "
            "unnecessary idle time, and review the coaching tip before the "
            "next high-load task."
        )
        action = "Review next-task coaching"

    else:
        # Generic answer only when the user did not ask a recognized question.
        if analysis.correlation:
            message = (
                "I found an evidence-backed pattern: elevated operator "
                "behaviour overlaps with machine signals in the same time window."
            )
            action = "Start 2-minute load handling lesson"
        elif analysis.health == "CRITICAL":
            message = (
                "The simulated machine signals are at a critical level. "
                "I can show you the evidence behind this alert."
            )
            action = "Review machine evidence before the next high-load task"
        elif analysis.health == "WARNING":
            message = (
                "A machine signal is above the prototype baseline. "
                "I can show you the evidence behind the alert."
            )
            action = "Review machine evidence"
        elif analysis.risk == "HIGH":
            message = (
                "Your operating pattern shows elevated risk signals "
                "compared with the prototype baseline."
            )
            action = "Review operator coaching"
        elif analysis.risk == "MEDIUM":
            message = (
                "Your operating pattern has some elevated signals "
                "compared with the prototype baseline."
            )
            action = "Review operator coaching"
        else:
            message = (
                "Your current operator and machine signals are within "
                "the prototype baseline ranges."
            )
            action = "Continue current operation"

    return CopilotResponse(
        message=message,
        risk=analysis.risk,
        health=analysis.health,
        confidence=analysis.confidence,
        action=action,
        evidence=evidence,
        correlation=analysis.correlation,
        correlation_note=analysis.correlation_note,
        risk_score=analysis.risk_score,
        evidence_detail=analysis.evidence_detail,
        intent=intent,
        question=question,
        ml_model=analysis.ml_model,
        ml_anomaly_score=analysis.ml_anomaly_score,
        ml_prediction=analysis.ml_prediction,
    )


async def fetch_module1(scenario: str, history_count: int = 8):
    async with httpx.AsyncClient(timeout=5.0) as client:
        current_response = await client.get(
            f"{MODULE1_URL}/telemetry",
            params={"scenario": scenario},
        )
        current_response.raise_for_status()
        current = current_response.json()

        history_response = await client.get(
            f"{MODULE1_URL}/telemetry/history",
            params={"scenario": "normal", "limit": history_count},
        )
        history_response.raise_for_status()
        history = history_response.json()
        return current, history


async def analyze_with_module2(current: dict, history: list[dict]) -> Analysis:
    payload = {"current": current, "history": history}

    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(
            f"{MODULE2_URL}/analyze",
            json=payload,
        )
        response.raise_for_status()
        return Analysis(**response.json())


@app.get("/")
def root():
    return {
        "module": "CATalyst Module 3 - AI Orchestrator",
        "status": "ok",
        "module1_url": MODULE1_URL,
        "module2_url": MODULE2_URL,
        "endpoints": [
            "/copilot",
            "/copilot/scenario/{scenario}",
            "/explain",
            "/schedule",
            "/coach",
        ],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "module": "module3",
        "module1_url": MODULE1_URL,
        "module2_url": MODULE2_URL,
    }


@app.get("/live/scenario/{scenario}", response_model=LiveResponse)
async def live_scenario(scenario: str):
    scenario_key = scenario.strip().lower()
    scenario_map = {
        "normal": "normal",
        "operator_risk": "operator_risk",
        "operation_to_wear": "harsh",
        "harsh": "harsh",
    }
    if scenario_key not in scenario_map:
        raise HTTPException(status_code=400, detail="Unknown scenario")
    try:
        current, history = await fetch_module1(scenario_map[scenario_key], history_count=60)
        analysis = await analyze_with_module2(current, history)
        return LiveResponse(telemetry=Telemetry(**current), analysis=analysis)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Live telemetry unavailable: {exc}") from exc


@app.post("/copilot", response_model=CopilotResponse)
async def copilot(data: Telemetry, intent: str = "status"):
    try:
        analysis = await analyze_with_module2(data.model_dump(), [])
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Module 2 is unavailable: {exc}",
        ) from exc

    return build_response(analysis, intent)


@app.post("/copilot/scenario/{scenario}", response_model=CopilotResponse)
async def copilot_scenario(
    scenario: str,
    question: str | None = Query(default=None, max_length=1000),
    intent: str = "status",
):
    scenario_key = scenario.strip().lower()

    scenario_map = {
        "normal": "normal",
        "operator_risk": "operator_risk",
        "operation_to_wear": "harsh",
        "harsh": "harsh",
    }

    if scenario_key not in scenario_map:
        raise HTTPException(
            status_code=400,
            detail="Unknown scenario. Use normal, operator_risk, or operation_to_wear.",
        )

    module1_scenario = scenario_map[scenario_key]

    try:
        current, history = await fetch_module1(module1_scenario, history_count=8)
        analysis = await analyze_with_module2(current, history)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Module 1 or Module 2 is unavailable: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Module 1 or Module 2 integration failed: {exc}",
        ) from exc

    # The actual transcript wins over any default intent.
    detected_intent = detect_intent(question) if question else (intent or "status")

    print(
        f"[CATalyst] question={question!r} intent={detected_intent!r} "
        f"scenario={scenario_key!r}"
    )

    return build_response(
        analysis,
        detected_intent,
        question=question,
    )


@app.post("/explain", response_model=CopilotResponse)
def explain(analysis: Analysis):
    return build_response(analysis, "why")


@app.post("/schedule")
def schedule(analysis: Analysis):
    if analysis.correlation or analysis.risk == "HIGH":
        return {
            "next_action": "2-minute load handling lesson",
            "priority": "HIGH",
            "when": "before next high-load task",
        }

    return {
        "next_action": "Normal operation check-in",
        "priority": "NORMAL",
        "when": "next task transition",
    }


@app.post("/coach")
def coach(analysis: Analysis):
    if analysis.correlation:
        return {
            "title": "Smoother load handling",
            "duration": "2 minutes",
            "steps": [
                "Approach the load smoothly.",
                "Avoid repeated aggressive high-load cycles.",
                "Pause and reassess if machine signals remain elevated.",
            ],
        }

    return {
        "title": "Good operating baseline",
        "duration": "1 minute",
        "steps": [
            "Maintain smooth control inputs.",
            "Keep unnecessary idle time low.",
        ],
    }
