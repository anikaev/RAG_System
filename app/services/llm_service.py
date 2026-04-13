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
        primary_provider_name = self._provider_name(self.primary_provider)
        try:
            result = self.primary_provider.generate(request)
            result = self._with_metadata(
                result,
                primary_provider=primary_provider_name,
            )
            return self._post_process(
                request,
                result,
                used_fallback=False,
                fallback_reason=None,
            )
        except Exception as exc:
            logger.warning(
                "llm.primary_failed",
                extra={
                    "event": "llm.primary_failed",
                    "mode": request.mode,
                    "error": str(exc),
                },
            )
            fallback_result = self.fallback_provider.generate(request)
            fallback_result = self._with_metadata(
                fallback_result,
                primary_provider=primary_provider_name,
            )
            return self._post_process(
                request,
                fallback_result,
                used_fallback=True,
                fallback_reason="primary_provider_failed",
            )

    def _post_process(
        self,
        request: LLMGenerationRequest,
        result: LLMGenerationResult,
        *,
        used_fallback: bool,
        fallback_reason: str | None,
    ) -> LLMGenerationResult:
        sanitized = self._sanitize_result(result)

        violation_reason = self._policy_violation_reason(request, sanitized.response_text)
        if violation_reason is not None:
            logger.warning(
                "llm.policy_violation_detected",
                extra={
                    "event": "llm.policy_violation_detected",
                    "mode": request.mode,
                    "reason": violation_reason,
                },
            )
            sanitized = self._safe_fallback_result(
                request,
                primary_provider=self._metadata_str(sanitized.metadata, "primary_provider"),
            )
            used_fallback = True
            fallback_reason = violation_reason

        metadata = dict(sanitized.metadata)
        metadata["fallback_used"] = used_fallback
        metadata["fallback_reason"] = fallback_reason
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

    def _safe_fallback_result(
        self,
        request: LLMGenerationRequest,
        *,
        primary_provider: str | None = None,
    ) -> LLMGenerationResult:
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
                metadata={
                    "provider": self._provider_name(self.fallback_provider),
                    "mode": request.mode,
                    "primary_provider": primary_provider,
                },
            )

        fallback_result = self.fallback_provider.generate(request)
        fallback_result = self._with_metadata(
            fallback_result,
            primary_provider=primary_provider,
        )
        return self._sanitize_result(fallback_result)

    @staticmethod
    def _policy_violation_reason(
        request: LLMGenerationRequest,
        response_text: str,
    ) -> str | None:
        code_blocks = _CODE_BLOCK_RE.findall(response_text)
        code_like_lines = len(_CODE_LINE_RE.findall(response_text))
        if request.mode == "code_feedback":
            return None

        lowered = response_text.lower()
        if request.refusal:
            if code_blocks or code_like_lines > 0:
                return "refusal_contains_code"
            return None

        if "готовое решение" in lowered or "готовый код" in lowered:
            return "contains_full_solution_phrase"

        if request.mode == "clarify":
            if code_blocks:
                return "clarify_contains_code_block"
            if code_like_lines >= 3:
                return "clarify_contains_code_like_lines"
            return None

        if request.mode == "hint_only":
            if request.hint_level < 4 and code_blocks:
                return "hint_only_contains_code_block"
            if code_like_lines >= 5:
                return "hint_only_contains_too_much_code"
            return None

        if request.mode == "concept_explainer":
            if len(code_blocks) > 1:
                return "concept_explainer_contains_multiple_code_blocks"
            if len(code_blocks) == 1:
                code_block = code_blocks[0]
                if code_block.count("\n") > 6 or len(code_block) > 320:
                    return "concept_explainer_contains_large_code_block"
            if code_like_lines >= 8:
                return "concept_explainer_contains_too_much_code"
            return None

        return None

    @staticmethod
    def _metadata_str(metadata: dict[str, object], key: str) -> str | None:
        value = metadata.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _provider_name(provider: LLMProvider) -> str:
        mapping = {
            "MockLLMProvider": "mock",
            "CompatibleAPILLMProvider": "compatible_api",
        }
        return mapping.get(type(provider).__name__, type(provider).__name__)

    @staticmethod
    def _with_metadata(
        result: LLMGenerationResult,
        *,
        primary_provider: str | None,
    ) -> LLMGenerationResult:
        metadata = dict(result.metadata)
        metadata.setdefault("primary_provider", primary_provider)
        return result.model_copy(update={"metadata": metadata})


class _SafeFormatMap(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
