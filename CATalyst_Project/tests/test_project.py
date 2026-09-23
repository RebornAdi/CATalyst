import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE1 = ROOT / "backend" / "module1_data_simulation"
MODULE2 = ROOT / "backend" / "module2_intelligence"
MODULE3 = ROOT / "backend" / "module3_orchestrator"


def load_module1():
    spec = importlib.util.spec_from_file_location("module1_app_for_test", MODULE1 / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_module2():
    sys.path.insert(0, str(MODULE2))
    from app.schemas import TelemetryReading
    from app.analyzer import analyze
    return TelemetryReading, analyze


def load_module3():
    app_path = MODULE3 / "app.py"
    spec = importlib.util.spec_from_file_location("module3_app_for_test", app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_response, module.Analysis


def test_module1_scenarios_match_module2_contract():
    module1 = load_module1()
    TelemetryReading, analyze = load_module2()

    normal = module1.make_telemetry("normal").model_dump()
    harsh = module1.make_telemetry("harsh").model_dump()

    for reading in (normal, harsh):
        parsed = TelemetryReading(**reading)
        result = analyze(parsed, [])
        assert result.risk in {"LOW", "MEDIUM", "HIGH"}
        assert result.health in {"OK", "WARNING", "CRITICAL"}
        assert 0 <= result.confidence <= 1
        assert isinstance(result.evidence, list)


def test_module2_operation_to_wear_contract():
    TelemetryReading, analyze = load_module2()

    with open(MODULE2 / "sample_data.json", encoding="utf-8") as f:
        data = json.load(f)

    block = data["OPERATION_TO_WEAR"]
    current = TelemetryReading(**block["current"])
    history = [TelemetryReading(**x) for x in block["history"]]
    result = analyze(current, history)

    assert result.correlation is True
    assert result.health in {"WARNING", "CRITICAL"}
    assert any("hydraulic" in item.lower() for item in result.evidence)
    assert result.correlation_note
    assert "not proven causation" in result.correlation_note.lower()


def test_module3_builds_operator_response():
    build_response, Analysis = load_module3()

    analysis = Analysis(
        risk="HIGH",
        health="CRITICAL",
        correlation=True,
        confidence=0.78,
        evidence=["7 harsh load cycles", "Hydraulic pressure above baseline"],
    )
    result = build_response(analysis, "why")

    assert result.risk == "HIGH"
    assert result.health == "CRITICAL"
    assert result.correlation is True
    assert result.evidence
    assert result.action
