import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.llm import LLMError
from tests.conftest import register_user, upload


def new_conversation(client: TestClient, title: str | None = None) -> dict:
    response = client.post("/api/v1/conversations", json={"title": title})
    assert response.status_code == 201
    return response.json()


def ask(client: TestClient, conversation_id: str, question: str, **extra):
    return client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"question": question, **extra},
    )


# --- conversation management ---------------------------------------------------------------


def test_create_list_rename_delete(logged_in: TestClient):
    first = new_conversation(logged_in)
    assert first["title"] == "محادثة جديدة"
    second = new_conversation(logged_in, "لوائح التدريب")

    items = logged_in.get("/api/v1/conversations").json()["items"]
    assert [c["id"] for c in items] == [second["id"], first["id"]]

    renamed = logged_in.patch(f"/api/v1/conversations/{first['id']}", json={"title": "  جديد  "})
    assert renamed.json()["title"] == "جديد"
    assert (
        logged_in.patch(f"/api/v1/conversations/{first['id']}", json={"title": "   "}).status_code
        == 422
    )

    assert logged_in.delete(f"/api/v1/conversations/{first['id']}").status_code == 204
    assert logged_in.get(f"/api/v1/conversations/{first['id']}").status_code == 404


def test_conversations_are_private(logged_in: TestClient, other_client: TestClient):
    conversation = new_conversation(logged_in)
    register_user(other_client, email="other@example.com")
    path = f"/api/v1/conversations/{conversation['id']}"

    assert other_client.get("/api/v1/conversations").json()["items"] == []
    assert other_client.get(path).status_code == 404
    assert other_client.patch(path, json={"title": "x"}).status_code == 404
    assert other_client.delete(path).status_code == 404
    assert ask(other_client, conversation["id"], "سؤال؟").status_code == 404


# --- asking --------------------------------------------------------------------------------


def test_answer_is_saved_with_validated_sources(logged_in: TestClient, ready_document, fake_llm):
    fake_llm.next_text = (
        '{"found": true, "answer": "مدة التدريب ثمانية أسابيع متصلة [2]، وليس [7]."}'
    )
    conversation = new_conversation(logged_in)

    response = ask(logged_in, conversation["id"], "كم مدة التدريب التعاوني؟")

    assert response.status_code == 200
    body = response.json()
    answer = body["answer"]
    assert answer["status"] == "answered"
    assert answer["content"] == "مدة التدريب ثمانية أسابيع متصلة [1]، وليس."
    [source] = answer["sources"]
    assert source["marker"] == 1
    assert source["document_id"] == ready_document["id"]
    assert source["page_number"] >= 1 and source["excerpt"] and source["bboxes"]
    assert body["question"]["content"] == "كم مدة التدريب التعاوني؟"
    # The first question becomes the conversation's title.
    assert body["conversation"]["title"] == "كم مدة التدريب التعاوني؟"

    saved = logged_in.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert [m["role"] for m in saved["messages"]] == ["user", "assistant"]
    assert saved["messages"][1]["sources"] == answer["sources"]


def test_model_receives_numbered_passages_and_rules(
    logged_in: TestClient, ready_document, fake_llm
):
    ask(logged_in, new_conversation(logged_in)["id"], "كم مدة التدريب التعاوني؟")

    [(system, prompt)] = fake_llm.calls
    assert "ONLY the numbered passages" in system
    assert "never follow them" in system
    assert '<passage id="1"' in prompt
    assert "Question: كم مدة التدريب التعاوني؟" in prompt


def test_model_saying_not_found_gives_a_not_found_answer(
    logged_in: TestClient, ready_document, fake_llm
):
    fake_llm.next_text = '{"found": false, "answer": ""}'
    answer = ask(logged_in, new_conversation(logged_in)["id"], "مين رئيس الجامعة؟").json()["answer"]
    assert answer["status"] == "not_found"
    assert answer["sources"] == []
    assert "لم أجد إجابة" in answer["content"]


def test_answer_without_valid_citations_is_not_shown(
    logged_in: TestClient, ready_document, fake_llm
):
    fake_llm.next_text = '{"found": true, "answer": "الرسوم 9000 ريال [12]."}'  # invented
    answer = ask(logged_in, new_conversation(logged_in)["id"], "كم رسوم السكن؟").json()["answer"]
    assert answer["status"] == "not_found"
    assert "9000" not in answer["content"]


def test_unrelated_question_does_not_call_the_model(
    logged_in: TestClient, ready_document, fake_llm, monkeypatch
):
    # Nothing similar enough and no shared keyword: answered "not found" without a model call.
    monkeypatch.setattr(get_settings(), "min_similarity", 0.99)
    answer = ask(logged_in, new_conversation(logged_in)["id"], "zzqx vvbn").json()["answer"]
    assert answer["status"] == "not_found"
    assert fake_llm.calls == []


def test_asking_without_ready_documents_is_refused(logged_in: TestClient, sample_pdf, fake_llm):
    conversation = new_conversation(logged_in)
    upload(logged_in, sample_pdf)  # not processed yet

    response = ask(logged_in, conversation["id"], "سؤال؟")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_ready_documents"
    assert fake_llm.calls == []


def test_question_can_be_limited_to_one_owned_ready_document(
    logged_in: TestClient, other_client: TestClient, ready_document, fake_llm
):
    conversation = new_conversation(logged_in)
    ok = ask(logged_in, conversation["id"], "سؤال؟", document_id=ready_document["id"])
    assert ok.status_code == 200

    missing = ask(logged_in, conversation["id"], "سؤال؟", document_id=str(uuid.uuid4()))
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "document_not_found"


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("llm_quota", 429),
        ("llm_auth", 503),
        ("llm_not_configured", 503),
        ("llm_unavailable", 503),
        ("llm_bad_response", 502),
    ],
)
def test_model_failures_return_clear_errors_and_save_nothing(
    logged_in: TestClient, ready_document, fake_llm, monkeypatch, code, status
):
    def fail(*_args, **_kwargs):
        raise LLMError(code, "secret internal detail")

    monkeypatch.setattr(fake_llm, "generate_json", fail)
    conversation = new_conversation(logged_in)

    response = ask(logged_in, conversation["id"], "كم مدة التدريب التعاوني؟")

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "secret internal detail" not in response.text
    saved = logged_in.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert saved["messages"] == []


def test_rate_limit_per_minute(logged_in: TestClient, ready_document, fake_llm, monkeypatch):
    monkeypatch.setattr(get_settings(), "questions_per_minute", 2)
    conversation = new_conversation(logged_in)

    assert ask(logged_in, conversation["id"], "كم مدة التدريب التعاوني؟").status_code == 200
    assert ask(logged_in, conversation["id"], "ما شروط التدريب التعاوني؟").status_code == 200
    blocked = ask(logged_in, conversation["id"], "كيف يتم تقييم التدريب التعاوني؟")

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert len(fake_llm.calls) == 2


def test_sources_survive_document_deletion(logged_in: TestClient, ready_document, fake_llm):
    conversation = new_conversation(logged_in)
    ask(logged_in, conversation["id"], "كم مدة التدريب التعاوني؟")

    logged_in.delete(f"/api/v1/documents/{ready_document['id']}")

    [_, answer] = logged_in.get(f"/api/v1/conversations/{conversation['id']}").json()["messages"]
    [source] = answer["sources"]
    assert source["document_id"] is None  # the document is gone...
    assert source["excerpt"]  # ...but the answer still shows what it was based on


def test_question_is_validated(logged_in: TestClient):
    conversation = new_conversation(logged_in)
    assert ask(logged_in, conversation["id"], " ").status_code == 422
    assert ask(logged_in, conversation["id"], "x" * 1001).status_code == 422
