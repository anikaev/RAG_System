from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.core.config import Settings
from app.core.security import redact_internal_paths
from app.providers.interfaces import CodeExecutionBackend, CodeExecutionRequest, CodeExecutionResult


@dataclass(frozen=True, slots=True)
class RunnerTestCase:
    stdin: str
    expected_stdout: str


@dataclass(frozen=True, slots=True)
class TaskTestSuite:
    public_tests: tuple[RunnerTestCase, ...]
    hidden_tests: tuple[RunnerTestCase, ...]


@dataclass(frozen=True, slots=True)
class RunOutcome:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


class DockerCodeExecutionBackend(CodeExecutionBackend):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(self, request: CodeExecutionRequest) -> CodeExecutionResult:
        ready, reason = self._ensure_runner_ready()
        if not ready:
            return CodeExecutionResult(
                status="not_run",
                runner_available=False,
                hidden_tests_summary="not_run",
                details={
                    "reason": reason,
                    "language": request.language,
                    "task_id": request.task_id,
                },
            )

        test_suite = self._load_test_suite(request.task_id)
        if test_suite is None:
            return self._run_smoke_execution(request)
        return self._run_test_suite(request, test_suite)

    def _run_smoke_execution(self, request: CodeExecutionRequest) -> CodeExecutionResult:
        outcome = self._run_case(request.code, stdin="")
        if outcome.timed_out:
            return self._timeout_result()
        if outcome.returncode != 0:
            return self._runtime_error_result(outcome.stderr)
        return CodeExecutionResult(
            status="validated",
            runner_available=True,
            hidden_tests_summary="not_configured",
            details={
                "stdout_excerpt": self._truncate(outcome.stdout),
            },
        )

    def _run_test_suite(
        self,
        request: CodeExecutionRequest,
        test_suite: TaskTestSuite,
    ) -> CodeExecutionResult:
        public_passed = 0
        public_total = len(test_suite.public_tests)

        for case in test_suite.public_tests:
            outcome = self._run_case(request.code, stdin=case.stdin)
            if outcome.timed_out:
                return self._timeout_result(
                    public_tests_passed=public_passed,
                    public_tests_total=public_total,
                )
            if outcome.returncode != 0:
                return self._runtime_error_result(
                    outcome.stderr,
                    public_tests_passed=public_passed,
                    public_tests_total=public_total,
                )
            if self._normalize_output(outcome.stdout) == self._normalize_output(case.expected_stdout):
                public_passed += 1

        hidden_summary = "not_configured"
        if test_suite.hidden_tests:
            hidden_passed = 0
            for case in test_suite.hidden_tests:
                outcome = self._run_case(request.code, stdin=case.stdin)
                if outcome.timed_out:
                    return self._timeout_result(
                        public_tests_passed=public_passed,
                        public_tests_total=public_total,
                    )
                if outcome.returncode == 0 and (
                    self._normalize_output(outcome.stdout)
                    == self._normalize_output(case.expected_stdout)
                ):
                    hidden_passed += 1
            hidden_summary = (
                "passed"
                if hidden_passed == len(test_suite.hidden_tests)
                else "failed"
            )

        status = "validated" if public_passed == public_total else "failed_tests"
        return CodeExecutionResult(
            status=status,
            public_tests_passed=public_passed,
            public_tests_total=public_total,
            hidden_tests_summary=hidden_summary,
            runner_available=True,
            details={},
        )

    def _run_case(self, code: str, *, stdin: str) -> RunOutcome:
        with TemporaryDirectory(prefix="rag-runner-") as tmpdir:
            tmp_path = Path(tmpdir)
            source_path = tmp_path / "user_code.py"
            source_path.write_text(code, encoding="utf-8")
            container_name = f"rag-runner-{uuid4().hex[:12]}"
            command = [
                self.settings.runner_binary,
                "run",
                "--rm",
                "--name",
                container_name,
                "--network",
                "none",
                "--cpus",
                str(self.settings.runner_cpu_limit),
                "--memory",
                f"{self.settings.runner_memory_mb}m",
                "--read-only",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=64m",
                "-v",
                f"{tmp_path}:{self.settings.runner_workdir}:ro",
                "-w",
                self.settings.runner_workdir,
                self.settings.runner_image,
                "python",
                "user_code.py",
            ]
            try:
                completed = subprocess.run(
                    command,
                    input=stdin,
                    capture_output=True,
                    text=True,
                    timeout=self.settings.runner_timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                self._cleanup_container(container_name)
                return RunOutcome(returncode=124, stdout="", stderr="", timed_out=True)

        return RunOutcome(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def _ensure_runner_ready(self) -> tuple[bool, str]:
        try:
            version = subprocess.run(
                [self.settings.runner_binary, "--version"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            return False, f"Docker CLI is unavailable: {exc}"

        if version.returncode != 0:
            return False, "Docker CLI is installed but not usable."

        image = subprocess.run(
            [
                self.settings.runner_binary,
                "image",
                "inspect",
                self.settings.runner_image,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if image.returncode != 0:
            return False, (
                "Runner image is not available. Build it with "
                f"`docker build -f docker/runner-python.Dockerfile -t {self.settings.runner_image} .`"
            )
        return True, "ok"

    def _load_test_suite(self, task_id: str | None) -> TaskTestSuite | None:
        if not task_id:
            return None
        test_file = self.settings.runner_tests_path / f"{task_id}.json"
        if not test_file.exists():
            return None

        payload = json.loads(test_file.read_text(encoding="utf-8"))
        public_tests = tuple(
            RunnerTestCase(
                stdin=str(item.get("stdin", "")),
                expected_stdout=str(item.get("expected_stdout", "")),
            )
            for item in payload.get("public_tests", [])
        )
        hidden_tests = tuple(
            RunnerTestCase(
                stdin=str(item.get("stdin", "")),
                expected_stdout=str(item.get("expected_stdout", "")),
            )
            for item in payload.get("hidden_tests", [])
        )
        return TaskTestSuite(
            public_tests=public_tests,
            hidden_tests=hidden_tests,
        )

    def _cleanup_container(self, container_name: str) -> None:
        subprocess.run(
            [
                self.settings.runner_binary,
                "rm",
                "-f",
                container_name,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    @staticmethod
    def _normalize_output(value: str) -> str:
        return value.strip().replace("\r\n", "\n")

    @staticmethod
    def _truncate(value: str, limit: int = 400) -> str:
        compact = redact_internal_paths(value.strip())
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 3].rstrip()}..."

    def _timeout_result(
        self,
        *,
        public_tests_passed: int = 0,
        public_tests_total: int = 0,
    ) -> CodeExecutionResult:
        return CodeExecutionResult(
            status="timeout",
            public_tests_passed=public_tests_passed,
            public_tests_total=public_tests_total,
            hidden_tests_summary="not_run",
            runner_available=True,
            details={"reason": "Execution timed out."},
        )

    def _runtime_error_result(
        self,
        stderr: str,
        *,
        public_tests_passed: int = 0,
        public_tests_total: int = 0,
    ) -> CodeExecutionResult:
        return CodeExecutionResult(
            status="runtime_error",
            public_tests_passed=public_tests_passed,
            public_tests_total=public_tests_total,
            hidden_tests_summary="not_run",
            runner_available=True,
            details={
                "stderr_excerpt": self._truncate(stderr),
            },
        )
