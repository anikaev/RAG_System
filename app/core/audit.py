from __future__ import annotations

import logging

from app.core.policies import normalize_text
from app.core.security import sanitize_excerpt

logger = logging.getLogger(__name__)

PROMPT_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous",
    "reveal system prompt",
    "show system prompt",
    "developer message",
    "system prompt",
    "bypass safety",
    "jailbreak",
    "покажи системный промпт",
    "раскрой системный промпт",
    "игнорируй предыдущие инструкции",
)


def has_prompt_injection_signal(text: str) -> bool:
    normalized = normalize_text(text)
    return any(pattern in normalized for pattern in PROMPT_INJECTION_PATTERNS)


def emit_audit_event(
    audit_type: str,
    *,
    session_id: str | None = None,
    mode: str | None = None,
    message_excerpt: str | None = None,
    runner_status: str | None = None,
) -> None:
    logger.warning(
        "audit.event",
        extra={
            "event": "audit.event",
            "audit_type": audit_type,
            "session_id": session_id,
            "mode": mode,
            "runner_status": runner_status,
            "message_excerpt": sanitize_excerpt(message_excerpt or ""),
        },
    )
