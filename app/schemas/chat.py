from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ChatMode(StrEnum):
    HINT_ONLY = "hint_only"
    CODE_FEEDBACK = "code_feedback"
    CONCEPT_EXPLAINER = "concept_explainer"
    CLARIFY = "clarify"
    REFUSE_FULL_SOLUTION = "refuse_full_solution"


class TaskContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(default="informatics", min_length=1, max_length=64)
    topic: str | None = Field(default=None, max_length=128)
    task_id: str | None = Field(default=None, max_length=128)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str | None = Field(default=None, max_length=128)
    user_id: str | None = Field(default=None, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    task_context: TaskContext | None = None


class ChatResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    mode: ChatMode
    response_text: str
    hint_level: int = Field(ge=0, le=4)
    confidence: float = Field(ge=0.0, le=1.0)
    guiding_question: str | None = None
    used_context_ids: list[str] = Field(default_factory=list)
    refusal: bool = False
