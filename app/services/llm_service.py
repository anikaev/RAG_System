from __future__ import annotations

import logging
import re

from app.core.policies import build_refusal_message
from app.core.security import redact_internal_paths
from app.providers.interfaces import LLMGenerationRequest, LLMGenerationResult, LLMProvider
from app.providers.mock_llm_provider import MockLLMProvider

logger = logging.getLogger(__name__)

_CODE_BLOCK_RE = re.compile(r"```[\s\S]+?```")
_CODE_LINE_RE = re.compile(r"(?m)^\s*(?:def |class |for |while |if |print\(|return |[A-Za-z_]\w*\s*=)")


class LLMService:
    """Safe wrapper around LLM providers.

    The service centralizes fallback behavior and post-processing so the rest
    of the chat flow does not depend on any single model backend.
    """

    def __init__(
        self,
        *,
        primary_provider: LLMProvider,
        fallback_provider: LLMProvider | None = None,
    ) -> None:
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider or MockLLMProvider()

    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        try:
            result = self.primary_provider.generate(request)
            return self._post_process(request, result, used_fallback=False)
        except Exception as exc:
            logger.warning(
                "llm.primary_failed mode=%s error=%s",
                request.mode,
                exc,
            )
            fallback_result = self.fallback_provider.generate(request)
            return self._post_process(request, fallback_result, used_fallback=True)

    def _post_process(
        self,
        request: LLMGenerationRequest,
        result: LLMGenerationResult,
        *,
        used_fallback: bool,
    ) -> LLMGenerationResult:
        sanitized = self._sanitize_result(result)

        if self._violates_policy(request, sanitized.response_text):
            logger.warning("llm.policy_violation_detected mode=%s", request.mode)
            sanitized = self._safe_fallback_result(request)
            used_fallback = True

        metadata = dict(sanitized.metadata)
        metadata["fallback_used"] = used_fallback
        return sanitized.model_copy(update={"metadata": metadata})

    @staticmethod
    def _sanitize_result(result: LLMGenerationResult) -> LLMGenerationResult:
        response_text = redact_internal_paths(result.response_text).strip()
        guiding_question = (
            redact_internal_paths(result.guiding_question).strip()
            if result.guiding_question
            else None
        )
        return result.model_copy(
            update={
                "response_text": response_text,
                "guiding_question": guiding_question,
            }
        )

    def _safe_fallback_result(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        if request.refusal:
            response_text = build_refusal_message()
            if request.response_template:
                variables = dict(request.response_template_variables)
                variables.setdefault(
                    "refusal_reason",
                    "Это не поможет тебе в обучении.",
                )
                response_text = request.response_template.format_map(_SafeFormatMap(variables))
            return LLMGenerationResult(
                response_text=response_text,
                guiding_question=request.guiding_question_hint,
                confidence=request.confidence_hint or 0.96,
                metadata={"provider": "llm_service", "mode": request.mode},
            )

        fallback_result = self.fallback_provider.generate(request)
        return self._sanitize_result(fallback_result)

    @staticmethod
    def _violates_policy(request: LLMGenerationRequest, response_text: str) -> bool:
        if request.mode == "code_feedback":
            return False

        lowered = response_text.lower()
        if request.refusal:
            return bool(_CODE_BLOCK_RE.search(response_text) or _CODE_LINE_RE.search(response_text))

        if request.mode in {"hint_only", "clarify", "concept_explainer"}:
            if _CODE_BLOCK_RE.search(response_text):
                return True
            if len(_CODE_LINE_RE.findall(response_text)) >= 3:
                return True
            if "готовое решение" in lowered or "готовый код" in lowered:
                return True

        return False


class _SafeFormatMap(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
