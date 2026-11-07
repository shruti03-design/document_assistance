import pytest

from app.services import qa

REFUNDS = "Refunds are issued within 30 days of purchase if the item is unused."
OFFICE = "Our office is open Monday to Friday from nine to five."


@pytest.fixture
def fake_llm(monkeypatch):
    """Replace the LLM call; record the messages it receives."""
    calls = []

    def generate_answer(messages):
        calls.append(messages)
        return "Refunds are issued within 30 days [1]."

    monkeypatch.setattr(qa, "generate_answer", generate_answer)
    return calls


def upload_txt(client, name, text):
    return client.post("/documents/upload", files={"file": (name, text.encode(), "text/plain")}).json()


def test_answer_is_grounded_in_retrieved_chunks(client, fake_llm):
    doc = upload_txt(client, "policy.txt", REFUNDS)

    response = client.post("/ask", json={"question": "How long do refunds take?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Refunds are issued within 30 days [1]."
    assert body["sources"][0]["document_id"] == doc["id"]
    assert body["sources"][0]["document_name"] == "policy.txt"
    assert body["sources"][0]["page_number"] == 1

    system, user = fake_llm[0]
    assert "ONLY" in system["content"]
    assert "[1] (document: policy.txt, page 1)" in user["content"]
    assert REFUNDS in user["content"]
    assert "Question: How long do refunds take?" in user["content"]


def test_no_documents_returns_fallback_without_calling_llm(client, fake_llm):
    response = client.post("/ask", json={"question": "What is the refund policy?"})

    assert response.status_code == 200
    assert response.json() == {"answer": qa.NO_CONTEXT_ANSWER, "sources": []}
    assert fake_llm == []


def test_document_filter_limits_context(client, fake_llm):
    upload_txt(client, "policy.txt", REFUNDS)
    office = upload_txt(client, "office.txt", OFFICE)

    response = client.post("/ask", json={"question": "refunds", "document_ids": [office["id"]]})

    sources = response.json()["sources"]
    assert sources and all(s["document_id"] == office["id"] for s in sources)
    assert REFUNDS not in fake_llm[0][1]["content"]


def test_top_k_limits_number_of_sources(client, fake_llm, monkeypatch):
    monkeypatch.setattr("app.config.settings.chunk_size", 60)
    monkeypatch.setattr("app.config.settings.chunk_overlap", 0)
    upload_txt(client, "policy.txt", " ".join([REFUNDS, OFFICE] * 3))

    response = client.post("/ask", json={"question": "refunds", "top_k": 2})

    assert len(response.json()["sources"]) == 2


@pytest.mark.parametrize(
    "payload",
    [{}, {"question": ""}, {"question": "   "}, {"question": "x" * 2001}, {"question": "hi", "top_k": 0}],
)
def test_invalid_requests_are_rejected(client, payload):
    assert client.post("/ask", json=payload).status_code == 422


def test_llm_failure_returns_502(client, monkeypatch):
    def broken(messages):
        raise qa.AnswerGenerationError("Answer generation failed: timeout")

    monkeypatch.setattr(qa, "generate_answer", broken)
    upload_txt(client, "policy.txt", REFUNDS)

    response = client.post("/ask", json={"question": "refunds?"})

    assert response.status_code == 502
    assert "timeout" in response.json()["detail"]


def test_generate_answer_calls_chat_completions(monkeypatch):
    from types import SimpleNamespace

    import openai

    from app.services import embeddings

    sent = {}

    def create(model, messages):
        sent.update(model=model, messages=messages)
        message = SimpleNamespace(content="  An answer [1].  ")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(embeddings, "get_client", lambda: fake)

    assert qa.generate_answer([{"role": "user", "content": "q"}]) == "An answer [1]."
    assert sent["model"] == qa.settings.chat_model

    def failing(model, messages):
        raise openai.APIConnectionError(request=None)

    fake.chat.completions.create = failing
    with pytest.raises(qa.AnswerGenerationError):
        qa.generate_answer([{"role": "user", "content": "q"}])
