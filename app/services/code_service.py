from __future__ import annotations

import ast

from app.core.config import Settings
from app.core.security import find_blocked_code_patterns, redact_internal_paths
from app.providers.interfaces import CodeExecutionBackend, CodeExecutionRequest, CodeExecutionResult
from app.schemas.code import (
    CodeCheckRequest,
    CodeCheckResponseData,
    CodeIssue,
    ExecutionStatus,
    ExecutionSummary,
    IssueSeverity,
)
from app.services.session_store import SessionStore


class CodeService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_store: SessionStore,
        code_backend: CodeExecutionBackend,
    ) -> None:
        self.settings = settings
        self.session_store = session_store
        self.code_backend = code_backend

    def check_code(self, request: CodeCheckRequest) -> CodeCheckResponseData:
        session = self.session_store.get_or_create(request.session_id, request.user_id)
        issues: list[CodeIssue] = []

        if len(request.code) > self.settings.max_code_length:
            issues.append(
                CodeIssue(
                    code="code_too_large",
                    message="Код превышает допустимый размер для MVP-проверки.",
                    severity=IssueSeverity.ERROR,
                )
            )
            response = self._build_response(
                session_id=session.session_id,
                accepted=False,
                issues=issues,
                summary=ExecutionSummary(
                    syntax_ok=False,
                    execution_status=ExecutionStatus.BLOCKED,
                    hidden_tests_summary="not_run",
                    runner_available=False,
                ),
                feedback_text="Сократи пример до минимально воспроизводимого фрагмента.",
            )
            self._store_exchange(session.session_id, request.code, response.feedback_text)
            return response

        blocked_patterns = find_blocked_code_patterns(
            request.code,
            self.settings.blocked_code_patterns,
        )
        if blocked_patterns:
            issues.extend(
                CodeIssue(
                    code="blocked_pattern",
                    message=f"Обнаружен небезопасный паттерн: {pattern}",
                    severity=IssueSeverity.ERROR,
                )
                for pattern in blocked_patterns
            )
            response = self._build_response(
                session_id=session.session_id,
                accepted=False,
                issues=issues,
                summary=ExecutionSummary(
                    syntax_ok=True,
                    execution_status=ExecutionStatus.BLOCKED,
                    hidden_tests_summary="not_run",
                    runner_available=False,
                ),
                feedback_text=(
                    "Этот фрагмент не будет запущен. Убери доступ к файловой системе, сети "
                    "или динамическое исполнение кода."
                ),
            )
            self._store_exchange(session.session_id, request.code, response.feedback_text)
            return response

        try:
            ast.parse(request.code)
        except SyntaxError as exc:
            issues.append(
                CodeIssue(
                    code="syntax_error",
                    message=exc.msg,
                    severity=IssueSeverity.ERROR,
                    line=exc.lineno,
                    column=exc.offset,
                )
            )
            response = self._build_response(
                session_id=session.session_id,
                accepted=False,
                issues=issues,
                summary=ExecutionSummary(
                    syntax_ok=False,
                    execution_status=ExecutionStatus.NOT_RUN,
                    hidden_tests_summary="not_run",
                    runner_available=False,
                ),
                feedback_text="Сначала исправь синтаксис, затем повтори проверку.",
            )
            self._store_exchange(session.session_id, request.code, response.feedback_text)
            return response

        execution_result = self.code_backend.execute(
            CodeExecutionRequest(
                language=request.language.value,
                code=request.code,
                task_id=request.task_id,
            )
        )
        accepted = execution_result.runner_available is False or execution_result.status == "validated"
        issues.extend(self._execution_issues(execution_result))
        feedback_text = self._build_execution_feedback(execution_result)
        execution_status = self._map_execution_status(execution_result)
        response = self._build_response(
            session_id=session.session_id,
            accepted=accepted,
            issues=issues,
            summary=ExecutionSummary(
                syntax_ok=True,
                execution_status=execution_status,
                public_tests_passed=execution_result.public_tests_passed,
                public_tests_total=execution_result.public_tests_total,
                hidden_tests_summary=execution_result.hidden_tests_summary,
                runner_available=execution_result.runner_available,
            ),
            feedback_text=feedback_text,
        )
        self._store_exchange(session.session_id, request.code, response.feedback_text)
        return response

    def _execution_issues(self, execution_result: CodeExecutionResult) -> list[CodeIssue]:
        if execution_result.status == "runtime_error":
            return [
                CodeIssue(
                    code="runtime_error",
                    message=execution_result.details.get(
                        "stderr_excerpt",
                        "Код завершился с ошибкой во время sandbox execution.",
                    ),
                    severity=IssueSeverity.ERROR,
                )
            ]
        if execution_result.status == "timeout":
            return [
                CodeIssue(
                    code="execution_timeout",
                    message="Исполнение было остановлено по timeout.",
                    severity=IssueSeverity.ERROR,
                )
            ]
        if execution_result.status == "failed_tests":
            return [
                CodeIssue(
                    code="public_tests_failed",
                    message="Не все публичные тесты пройдены.",
                    severity=IssueSeverity.WARNING,
                )
            ]
        return []

    @staticmethod
    def _map_execution_status(execution_result: CodeExecutionResult) -> ExecutionStatus:
        if not execution_result.runner_available:
            return ExecutionStatus.NOT_RUN
        if execution_result.status == "timeout":
            return ExecutionStatus.BLOCKED
        return ExecutionStatus.VALIDATED

    @staticmethod
    def _build_execution_feedback(execution_result: CodeExecutionResult) -> str:
        if not execution_result.runner_available:
            return redact_internal_paths(
                "Синтаксис корректен. На этом этапе выполнена только безопасная статическая проверка; "
                "sandbox runner недоступен, поэтому код не исполнялся."
            )
        if execution_result.status == "validated":
            if execution_result.public_tests_total > 0:
                return (
                    "Код выполнился в sandbox и прошёл публичные тесты. "
                    "Проверь, что решение остаётся устойчивым на других входах."
                )
            return "Код выполнился в sandbox без ошибок."
        if execution_result.status == "failed_tests":
            return (
                "Код выполнился в sandbox, но не прошёл все публичные тесты. "
                "Проверь обработку крайних случаев и ожидаемый вывод."
            )
        if execution_result.status == "runtime_error":
            stderr_excerpt = execution_result.details.get(
                "stderr_excerpt",
                "Произошла ошибка во время исполнения.",
            )
            return redact_internal_paths(
                f"Код выполнился в sandbox, но завершился с ошибкой: {stderr_excerpt}"
            )
        if execution_result.status == "timeout":
            return (
                "Исполнение было остановлено по timeout. "
                "Проверь бесконечные циклы и слишком тяжёлые вычисления."
            )
        return "Sandbox execution завершилась в неопределённом состоянии."

    def _build_response(
        self,
        *,
        session_id: str,
        accepted: bool,
        issues: list[CodeIssue],
        summary: ExecutionSummary,
        feedback_text: str,
    ) -> CodeCheckResponseData:
        return CodeCheckResponseData(
            session_id=session_id,
            accepted=accepted,
            summary=summary,
            issues=issues,
            feedback_text=feedback_text,
            sanitized=True,
        )

    def _store_exchange(self, session_id: str, code: str, feedback_text: str) -> None:
        self.session_store.append_message(
            session_id,
            role="user",
            content=code,
            message_type="code_submission",
        )
        self.session_store.append_message(
            session_id,
            role="assistant",
            content=feedback_text,
            message_type="code_feedback",
        )
