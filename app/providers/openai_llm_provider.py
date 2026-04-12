from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import Settings
from app.core.security import sanitize_excerpt
from app.providers.interfaces import LLMGenerationRequest, LLMGenerationResult, LLMProvider

_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


class OpenAILLMProvider(LLMProvider):
    """OpenAI-backed provider with JSON-only structured output parsing."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        api_key = self.settings.openai_api_key
        if not api_key:
            raise RuntimeError("RAG_OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional runtime package
            raise RuntimeError("openai package is not installed.") from exc

        client = OpenAI(
            api_key=api_key,
            base_url=self.settings.openai_base_url or None,
        )
        response = client.responses.create(
            model=self.settings.openai_model,
            instructions=self._build_instructions(request),
            input=self._build_input(request),
        )

        output_text = getattr(response, "output_text", None)
        if not output_text:
            raise RuntimeError("OpenAI response did not include output_text.")

        payload = self._parse_payload(output_text)
        confidence = payload.get("confidence", request.confidence_hint or 0.55)
        confidence_value = min(max(float(confidence), 0.0), 1.0)

        return LLMGenerationResult(
            response_text=str(payload["response_text"]).strip(),
            guiding_question=self._normalize_optional_str(
                payload.get("guiding_question", request.guiding_question_hint)
            ),
            confidence=confidence_value,
            metadata={
                "provider": "openai",
                "mode": request.mode,
                "model": self.settings.openai_model,
                "response_id": getattr(response, "id", None),
            },
        )

    def _build_instructions(self, request: LLMGenerationRequest) -> str:
        parts = [
            "You are a safe tutoring assistant for EGE informatics.",
            "Return only valid JSON.",
            (
                'Use the exact schema: '
                '{"response_text": string, "guiding_question": string|null, "confidence": number}.'
            ),
        ]
        if request.pedagogical_instruction:
            parts.append(f"Pedagogical instruction: {request.pedagogical_instruction}")
        if request.hint_level_description:
            parts.append(f"Hint level: {request.hint_level_description}")
        if request.refusal:
            parts.append("Do not provide a full solution, final code, or final answer.")
        return "\n".join(parts)

    @staticmethod
    def _build_input(request: LLMGenerationRequest) -> str:
        context_lines = [
            f"- {sanitize_excerpt(item.content)}"
            for item in request.context
        ]
        context_block = "\n".join(context_lines) if context_lines else "- none"
        template_block = request.response_template or "none"
        return (
            f"Mode: {request.mode}\n"
            f"User message: {request.user_message}\n"
            f"Guiding question hint: {request.guiding_question_hint or 'none'}\n"
            f"Response template: {template_block}\n"
            f"Template variables: {json.dumps(request.response_template_variables, ensure_ascii=False)}\n"
            f"Retrieved context:\n{context_block}\n"
        )

    @staticmethod
    def _parse_payload(output_text: str) -> dict[str, Any]:
        match = _JSON_BLOCK_RE.search(output_text)
        candidate = match.group(0) if match else output_text
        payload = json.loads(candidate)
        if not isinstance(payload, dict):
            raise RuntimeError("OpenAI response payload is not a JSON object.")
        if "response_text" not in payload:
            raise RuntimeError("OpenAI response payload does not include response_text.")
        return payload

    @staticmethod
    def _normalize_optional_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
