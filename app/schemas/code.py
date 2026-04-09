from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SupportedLanguage(StrEnum):
    PYTHON = "python"


class IssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ExecutionStatus(StrEnum):
    NOT_RUN = "not_run"
    BLOCKED = "blocked"
    VALIDATED = "validated"


class CodeCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str | None = Field(default=None, max_length=128)
    user_id: str | None = Field(default=None, max_length=128)
    language: SupportedLanguage
    code: str = Field(min_length=1, max_length=12000)
    task_id: str | None = Field(default=None, max_length=128)


class CodeIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    severity: IssueSeverity
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)


class ExecutionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    syntax_ok: bool
    execution_status: ExecutionStatus
    public_tests_passed: int = Field(default=0, ge=0)
    public_tests_total: int = Field(default=0, ge=0)
    hidden_tests_summary: str = "not_run"
    runner_available: bool = False


class CodeCheckResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    accepted: bool
    summary: ExecutionSummary
    issues: list[CodeIssue] = Field(default_factory=list)
    feedback_text: str
    sanitized: bool = True
