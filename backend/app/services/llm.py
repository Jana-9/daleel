"""Language-model providers that write answers. The app depends only on `LLMProvider`.

The model is asked for JSON ({"found": bool, "answer": str}); the provider just returns text,
and `rag_service` parses and validates it, so a provider never decides what counts as cited.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

ANSWER_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "found": {
            "type": "BOOLEAN",
            "description": "true only if the passages contain the information to answer.",
        },
        "answer": {
            "type": "STRING",
            "description": "The answer, with [n] after each claim; empty when found is false.",
        },
    },
    "required": ["found", "answer"],
}


class LLMError(Exception):
    """A failure talking to the model, with a stable code the API can return."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code


@dataclass(frozen=True)
class LLMResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProvider(Protocol):
    model_name: str

    def generate_json(self, system: str, prompt: str) -> LLMResult: ...


class GeminiProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float,
        transport: httpx.BaseTransport | None = None,  # tests pass a mock transport
    ) -> None:
        self.model_name = model
        self._client = httpx.Client(
            transport=transport,
            base_url=GEMINI_BASE_URL,
            # The key goes in a header, never in the URL, so it cannot end up in access logs.
            # This also works for the newer "AQ." auth keys that AI Studio issues.
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )

    def generate_json(self, system: str, prompt: str) -> LLMResult:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,  # answers should be faithful, not creative
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
                "responseSchema": ANSWER_SCHEMA,
            },
        }
        try:
            response = self._client.post(f"/models/{self.model_name}:generateContent", json=body)
        except httpx.TimeoutException as exc:
            raise LLMError("llm_unavailable", "timeout") from exc
        except httpx.HTTPError as exc:
            raise LLMError("llm_unavailable", repr(exc)) from exc

        if response.status_code == 429:
            raise LLMError("llm_quota", response.text[:500])
        if response.status_code in (401, 403):
            raise LLMError("llm_auth", response.text[:500])
        if response.status_code == 404:
            raise LLMError("llm_model_not_found", response.text[:500])
        if response.status_code >= 400:
            raise LLMError("llm_unavailable", f"{response.status_code} {response.text[:500]}")
        return self._parse(response.json())

    @staticmethod
    def _parse(data: dict) -> LLMResult:
        candidates = data.get("candidates") or []
        if not candidates:
            reason = (data.get("promptFeedback") or {}).get("blockReason", "no candidates")
            raise LLMError("llm_bad_response", str(reason))
        parts = (candidates[0].get("content") or {}).get("parts") or []
        # Newer models may return "thought" parts (their reasoning); only the answer is wanted.
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not text.strip():
            raise LLMError("llm_bad_response", f"empty ({candidates[0].get('finishReason')})")
        usage = data.get("usageMetadata") or {}
        return LLMResult(
            text=text,
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
        )

    def list_models(self) -> list[str]:
        """Model IDs this key can use to generate text (for the setup check script)."""
        response = self._client.get("/models", params={"pageSize": 1000})
        response.raise_for_status()
        return sorted(
            m["name"].removeprefix("models/")
            for m in response.json().get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        )


class FakeLLMProvider:
    """Deterministic stand-in for tests: cites passage [1], or returns `next_text` if set."""

    model_name = "fake-llm-v1"

    def __init__(self) -> None:
        self.next_text: str | None = None
        self.calls: list[tuple[str, str]] = []

    def generate_json(self, system: str, prompt: str) -> LLMResult:
        self.calls.append((system, prompt))
        if self.next_text is not None:
            return LLMResult(self.next_text, 100, 20)
        return LLMResult(
            '{"found": true, "answer": "حسب الوثيقة، الإجابة موجودة هنا [1]."}', 100, 20
        )


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "fake":
        return FakeLLMProvider()
    if settings.gemini_api_key is None or not settings.gemini_api_key.get_secret_value():
        raise LLMError("llm_not_configured", "GEMINI_API_KEY is not set")
    return GeminiProvider(
        settings.gemini_api_key.get_secret_value(),
        settings.gemini_model,
        settings.llm_timeout_seconds,
    )
