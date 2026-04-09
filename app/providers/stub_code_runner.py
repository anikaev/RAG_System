from __future__ import annotations

from app.providers.interfaces import CodeExecutionBackend, CodeExecutionRequest, CodeExecutionResult


class LocalStubCodeRunner(CodeExecutionBackend):
    def execute(self, request: CodeExecutionRequest) -> CodeExecutionResult:
        return CodeExecutionResult(
            status="not_run",
            runner_available=False,
            hidden_tests_summary="not_run",
            details={
                "reason": "Sandbox execution backend is not configured yet.",
                "language": request.language,
                "task_id": request.task_id,
            },
        )
