import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE3 = ROOT / "backend" / "module3_orchestrator" / "app.py"


def load_module3():
    spec = importlib.util.spec_from_file_location("module3_voice_test", MODULE3)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_voice_questions_route_to_different_intents():
    m = load_module3()

    assert m.detect_intent("Why was I flagged?") == "why"
    assert m.detect_intent("Is my machine okay?") == "machine"
    assert m.detect_intent("How am I doing today?") == "operator"
    assert m.detect_intent("What should I do for the rest of my shift?") == "day"
    assert m.detect_intent("Why is hydraulic pressure high?") == "why"


def test_voice_question_changes_response():
    m = load_module3()

    analysis = m.Analysis(
        risk="HIGH",
        health="CRITICAL",
        correlation=True,
        confidence=0.88,
        evidence=[
            "Hydraulic pressure 250 = 2.3x baseline",
            "Vibration 0.8 = 2.4x baseline",
            "1 safety event detected",
        ],
    )

    why = m.build_response(
        analysis,
        m.detect_intent("Why was I flagged?"),
        "Why was I flagged?",
    )
    machine = m.build_response(
        analysis,
        m.detect_intent("Is my machine okay?"),
        "Is my machine okay?",
    )
    operator = m.build_response(
        analysis,
        m.detect_intent("How am I doing today?"),
        "How am I doing today?",
    )
    day = m.build_response(
        analysis,
        m.detect_intent("What should I do for the rest of my shift?"),
        "What should I do for the rest of my shift?",
    )

    messages = {why.message, machine.message, operator.message, day.message}
    assert len(messages) == 4
    assert why.intent == "why"
    assert machine.intent == "machine"
    assert operator.intent == "operator"
    assert day.intent == "day"
