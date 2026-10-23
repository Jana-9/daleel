"""Check that GEMINI_API_KEY (from backend/.env) works, without printing the key.

    uv run python -m scripts.check_gemini

Lists the text models the key can use and sends one tiny test question to GEMINI_MODEL.
"""

import sys

from app.core.config import get_settings
from app.services.llm import GeminiProvider, LLMError


def main() -> int:
    settings = get_settings()
    key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
    if not key:
        print("GEMINI_API_KEY is not set. Add it to backend/.env (see .env.example).")
        return 1
    print(f"Key found ({len(key)} characters, starts with {key[:3]}...).")

    provider = GeminiProvider(key, settings.gemini_model, settings.llm_timeout_seconds)
    try:
        models = provider.list_models()
    except Exception as exc:  # noqa: BLE001 - report any failure in plain words
        print(f"Could not list models: {exc}")
        print("The key may be invalid or revoked. Create a new one at aistudio.google.com/apikey")
        return 1
    flash = [m for m in models if "flash" in m]
    print(f"This key can use {len(models)} text models. Flash models: {', '.join(flash) or '-'}")

    if settings.gemini_model not in models:
        print(f"\nGEMINI_MODEL={settings.gemini_model} is NOT available for this key.")
        print("Set GEMINI_MODEL in backend/.env to one of the Flash-Lite models listed above.")
        return 1

    try:
        result = provider.generate_json(
            'Reply with JSON {"found": true, "answer": "..."}.', "Say hello in Arabic."
        )
    except LLMError as exc:
        print(f"\nTest question failed: {exc.code} {exc}")
        return 1
    print(f"\nTest question OK with {settings.gemini_model}: {result.text.strip()[:200]}")
    print("Answering is ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
