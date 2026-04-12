from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.providers.docker_code_runner import (
    DockerCodeExecutionBackend,
    RunOutcome,
    RunnerTestCase,
    TaskTestSuite,
)
from app.providers.interfaces import CodeExecutionRequest


def test_docker_runner_reports_unavailable_when_image_is_missing(tmp_path: Path):
    settings = Settings(
        runner_binary="missing-docker-binary",
        runner_tests_path=tmp_path,
    )
    backend = DockerCodeExecutionBackend(settings)

    result = backend.execute(
        CodeExecutionRequest(language="python", code="print(1)")
    )

    assert result.status == "not_run"
    assert result.runner_available is False


def test_docker_runner_uses_public_and_hidden_tests(monkeypatch, tmp_path: Path):
    settings = Settings(
        runner_tests_path=tmp_path,
    )
    backend = DockerCodeExecutionBackend(settings)

    monkeypatch.setattr(backend, "_ensure_runner_ready", lambda: (True, "ok"))
    monkeypatch.setattr(
        backend,
        "_load_test_suite",
        lambda task_id: TaskTestSuite(
            public_tests=(RunnerTestCase(stdin="2 3\n", expected_stdout="5\n"),),
            hidden_tests=(RunnerTestCase(stdin="10 -4\n", expected_stdout="6\n"),),
        ),
    )
    monkeypatch.setattr(
        backend,
        "_run_case",
        lambda code, stdin: RunOutcome(
            returncode=0,
            stdout="5\n" if stdin == "2 3\n" else "6\n",
            stderr="",
        ),
    )

    result = backend.execute(
        CodeExecutionRequest(
            language="python",
            code="a, b = map(int, input().split()); print(a + b)",
            task_id="demo-sum",
        )
    )

    assert result.status == "validated"
    assert result.runner_available is True
    assert result.public_tests_passed == 1
    assert result.public_tests_total == 1
    assert result.hidden_tests_summary == "passed"


def test_docker_runner_returns_timeout_status(monkeypatch, tmp_path: Path):
    settings = Settings(
        runner_tests_path=tmp_path,
    )
    backend = DockerCodeExecutionBackend(settings)

    monkeypatch.setattr(backend, "_ensure_runner_ready", lambda: (True, "ok"))
    monkeypatch.setattr(
        backend,
        "_load_test_suite",
        lambda task_id: TaskTestSuite(
            public_tests=(RunnerTestCase(stdin="", expected_stdout=""),),
            hidden_tests=(),
        ),
    )
    monkeypatch.setattr(
        backend,
        "_run_case",
        lambda code, stdin: RunOutcome(returncode=124, stdout="", stderr="", timed_out=True),
    )

    result = backend.execute(
        CodeExecutionRequest(language="python", code="while True:\n    pass", task_id="demo-sum")
    )

    assert result.status == "timeout"
    assert result.runner_available is True
