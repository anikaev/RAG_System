from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from app.core.config import Settings
from app.core.security import sanitize_excerpt
from app.providers.interfaces import LLMGenerationRequest, LLMGenerationResult, LLMProvider


class CompatibleAPILLMProvider(LLMProvider):
    """Generic provider for OpenAI-compatible APIs serving open-source models."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, request_payload: LLMGenerationRequest) -> LLMGenerationResult:
        base_url = self.settings.llm_api_base_url
        if not base_url:
            raise RuntimeError("RAG_LLM_API_BASE_URL is not configured.")

        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        body = json.dumps(
            {
                "model": self.settings.llm_model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": self._build_instructions(request_payload),
                    },
                    {
                        "role": "user",
                        "content": self._build_input(request_payload),
                    },
                ],
                "temperature": 0.2,
                "response_format": self._build_response_format(),
            }
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"

        http_request = request.Request(
            endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(
                http_request,
                timeout=self.settings.llm_api_timeout_seconds,
            ) as response:
                raw_payload = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise RuntimeError(f"Compatible LLM API request failed: {exc}") from exc

        message = self._extract_message(raw_payload)
        structured = self._parse_structured_message(message)
        confidence = structured.get("confidence", request_payload.confidence_hint or 0.55)
        confidence_value = min(max(float(confidence), 0.0), 1.0)

        return LLMGenerationResult(
            response_text=str(structured["response_text"]).strip(),
            guiding_question=self._normalize_optional_str(
                structured.get("guiding_question", request_payload.guiding_question_hint)
            ),
            confidence=confidence_value,
            metadata={
                "provider": "compatible_api",
                "mode": request_payload.mode,
                "model": self.settings.llm_model_name,
            },
        )

    def _build_instructions(self, request_payload: LLMGenerationRequest) -> str:
        parts = [
            "You are a safe tutoring assistant for EGE informatics.",
            "Return only valid JSON.",
            (
                'Use the exact schema: '
                '{"response_text": string, "guiding_question": string|null, "confidence": number}.'
            ),
        ]
        if request_payload.pedagogical_instruction:
            parts.append(
                f"Pedagogical instruction: {request_payload.pedagogical_instruction}"
            )
        if request_payload.hint_level_description:
            parts.append(f"Hint level: {request_payload.hint_level_description}")
        if request_payload.refusal:
            parts.append("Do not provide a full solution, final code, or final answer.")
        return "\n".join(parts)

    def _build_response_format(self) -> dict[str, Any]:
        if self.settings.llm_response_format_mode == "json_schema":
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": "rag_tutor_response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "response_text": {"type": "string"},
                            "guiding_question": {
                                "type": ["string", "null"],
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                            },
                        },
                        "required": [
                            "response_text",
                            "guiding_question",
                            "confidence",
                        ],
                        "additionalProperties": False,
                    },
                },
            }
        return {"type": "json_object"}

    @staticmethod
    def _build_input(request_payload: LLMGenerationRequest) -> str:
        context_lines = [
            f"- {sanitize_excerpt(item.content)}"
            for item in request_payload.context
        ]
        context_block = "\n".join(context_lines) if context_lines else "- none"
        template_block = request_payload.response_template or "none"
        variables_block = json.dumps(
            request_payload.response_template_variables,
            ensure_ascii=False,
        )
        return (
            f"Mode: {request_payload.mode}\n"
            f"User message: {request_payload.user_message}\n"
            f"Guiding question hint: {request_payload.guiding_question_hint or 'none'}\n"
            f"Response template: {template_block}\n"
            f"Template variables: {variables_block}\n"
            f"Retrieved context:\n{context_block}\n"
        )

    @staticmethod
    def _extract_message(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("Compatible LLM API did not return choices.")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise RuntimeError("Compatible LLM API returned malformed choice payload.")
        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise RuntimeError("Compatible LLM API returned malformed message payload.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Compatible LLM API returned empty message content.")
        return content

    @staticmethod
    def _parse_structured_message(message: str) -> dict[str, Any]:
        payload = json.loads(message)
        if not isinstance(payload, dict):
            raise RuntimeError("Compatible LLM payload is not a JSON object.")
        if "response_text" not in payload:
            raise RuntimeError("Compatible LLM payload does not include response_text.")
        return payload

    @staticmethod
    def _normalize_optional_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
