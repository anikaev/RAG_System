from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.providers.interfaces import CodeExecutionResult


def _load_scenarios() -> list[dict[str, Any]]:
    path = Path(__file__).with_name("scenarios.json")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "scenario",
    _load_scenarios(),
    ids=lambda scenario: str(scenario["name"]),
)
def test_golden_main_workflows(client, monkeypatch, scenario: dict[str, Any]) -> None:
    backend_override = scenario.get("backend_override")
    if backend_override == "failed_tests":
        backend = client.app.state.services.code_service.code_backend

        def fake_execute(_request: Any) -> CodeExecutionResult:
            return CodeExecutionResult(
                status="failed_tests",
                public_tests_passed=0,
                public_tests_total=1,
                hidden_tests_summary="not_run",
                runner_available=True,
            )

        monkeypatch.setattr(backend, "execute", fake_execute)

    response = client.request(
        scenario["method"],
        scenario["endpoint"],
        json=scenario["request_json"],
    )

    assert response.status_code == scenario["expected_status"]

    payload = response.json()
    assert payload["ok"] is scenario["expected_ok"]

    if payload["ok"]:
        data = payload["data"]
        expected_mode = scenario.get("expected_mode")
        if expected_mode is not None:
            assert data["mode"] == expected_mode

        expected_refusal = scenario.get("expected_refusal")
        if expected_refusal is not None:
            assert data["refusal"] is expected_refusal

        expected_hint_level = scenario.get("expected_hint_level")
        if expected_hint_level is not None:
            assert data["hint_level"] == expected_hint_level

        expected_accepted = scenario.get("expected_accepted")
        if expected_accepted is not None:
            assert data["accepted"] is expected_accepted

        for fragment in scenario.get("expected_response_contains", []):
            assert fragment in data["response_text"]

        for fragment in scenario.get("expected_feedback_contains", []):
            assert fragment in data["feedback_text"]

        expected_issue_codes = scenario.get("expected_issue_codes", [])
        if expected_issue_codes:
            actual_codes = [issue["code"] for issue in data["issues"]]
            assert actual_codes == expected_issue_codes
    else:
        error = payload["error"]
        assert error["code"] == scenario["expected_error_code"]
        assert error["message"] == scenario["expected_error_message"]
