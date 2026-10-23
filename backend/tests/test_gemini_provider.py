"""The Gemini client, tested against a fake HTTP server (no network, no API key)."""

import json

import httpx
import pytest

from app.services.llm import GeminiProvider, LLMError


def provider_with(handler) -> GeminiProvider:
    return GeminiProvider(
        "test-key", "gemini-test-model", timeout=5, transport=httpx.MockTransport(handler)
    )


def ok_response(parts: list[dict], usage: dict | None = None) -> httpx.Response:
    body = {
        "candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": "STOP"}],
        "usageMetadata": usage or {"promptTokenCount": 120, "candidatesTokenCount": 30},
    }
    return httpx.Response(200, json=body)


def test_sends_key_in_header_and_requests_json():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = request
        return ok_response([{"text": '{"found": true, "answer": "x [1]"}'}])

    result = provider_with(handler).generate_json("system rules", "the prompt")

    request = seen["request"]
    assert request.url.path == "/v1beta/models/gemini-test-model:generateContent"
    assert request.headers["x-goog-api-key"] == "test-key"
    assert "key=" not in str(request.url)  # never in the URL
    body = json.loads(request.content)
    assert body["systemInstruction"]["parts"][0]["text"] == "system rules"
    assert body["contents"][0]["parts"][0]["text"] == "the prompt"
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert result.text == '{"found": true, "answer": "x [1]"}'
    assert (result.input_tokens, result.output_tokens) == (120, 30)


def test_ignores_thought_parts():
    def handler(_: httpx.Request) -> httpx.Response:
        return ok_response([{"text": "thinking...", "thought": True}, {"text": '{"a": 1}'}])

    assert provider_with(handler).generate_json("s", "p").text == '{"a": 1}'


@pytest.mark.parametrize(
    ("status", "code"),
    [(429, "llm_quota"), (401, "llm_auth"), (403, "llm_auth"), (404, "llm_model_not_found"),
     (500, "llm_unavailable")],
)  # fmt: skip
def test_http_errors_map_to_codes(status, code):
    provider = provider_with(lambda _: httpx.Response(status, json={"error": {"message": "x"}}))
    with pytest.raises(LLMError) as error:
        provider.generate_json("s", "p")
    assert error.value.code == code


def test_blocked_or_empty_responses_are_errors():
    blocked = provider_with(
        lambda _: httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})
    )
    with pytest.raises(LLMError) as error:
        blocked.generate_json("s", "p")
    assert error.value.code == "llm_bad_response"

    empty = provider_with(lambda _: ok_response([{"text": "   "}]))
    with pytest.raises(LLMError):
        empty.generate_json("s", "p")


def test_timeouts_are_reported_as_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(LLMError) as error:
        provider_with(handler).generate_json("s", "p")
    assert error.value.code == "llm_unavailable"


def test_list_models_returns_text_generation_models():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "models": [
                    {"name": "models/b-model", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/embedder", "supportedGenerationMethods": ["embedContent"]},
                    {"name": "models/a-model", "supportedGenerationMethods": ["generateContent"]},
                ]
            },
        )

    assert provider_with(handler).list_models() == ["a-model", "b-model"]
