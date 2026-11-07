from app.services import embeddings, vector_store
from app.services.embeddings import EmbeddingError

from tests.conftest import fake_vector

REFUNDS = "Refunds are issued within 30 days of purchase if the item is unused."
SHIPPING = "Shipping takes five business days and is free on orders over fifty dollars."


def upload_txt(client, name: str, text: str) -> dict:
    response = client.post("/documents/upload", files={"file": (name, text.encode(), "text/plain")})
    assert response.status_code == 201
    return response.json()


def test_upload_indexes_document_into_qdrant(client, fake_embeddings):
    doc = upload_txt(client, "policy.txt", f"{REFUNDS}\n\n{SHIPPING}")

    # Background task runs after the response; TestClient waits for it
    doc = client.get(f"/documents/{doc['id']}").json()
    assert doc["status"] == "ready"
    assert doc["error"] is None
    assert doc["page_count"] == 1

    chunks = client.get(f"/documents/{doc['id']}/chunks").json()
    assert len(chunks) >= 1
    assert sum(len(batch) for batch in fake_embeddings) == len(chunks)

    hits = vector_store.search(fake_vector("refunds within 30 days"), limit=1)
    assert hits[0].document_id == doc["id"]
    assert hits[0].document_name == "policy.txt"
    assert hits[0].page_number == 1
    assert "Refunds" in hits[0].text


def test_search_returns_most_similar_chunk_and_filters_by_document(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.chunk_size", 100)
    monkeypatch.setattr("app.config.settings.chunk_overlap", 0)
    doc_a = upload_txt(client, "a.txt", f"{REFUNDS}\n\n{SHIPPING}")
    doc_b = upload_txt(client, "b.txt", "Our office is open Monday to Friday from nine to five.")

    hits = vector_store.search(fake_vector("how long does shipping take"), limit=3)
    assert "Shipping" in hits[0].text
    assert hits[0].score >= hits[-1].score

    only_b = vector_store.search(fake_vector("shipping"), limit=5, document_ids=[doc_b["id"]])
    assert only_b and all(h.document_id == doc_b["id"] for h in only_b)
    assert doc_a["id"] != doc_b["id"]


def test_reindexing_replaces_old_vectors(client):
    from app.db import SessionLocal
    from app.models import Document
    from app.services.indexing import index_document

    doc = upload_txt(client, "policy.txt", REFUNDS)
    with SessionLocal() as db:
        index_document(db, db.get(Document, doc["id"]))  # index the same document again

    hits = vector_store.search(fake_vector(REFUNDS), limit=10, document_ids=[doc["id"]])
    chunks = client.get(f"/documents/{doc['id']}/chunks").json()
    assert len(hits) == len(chunks)  # no leftover vectors from the first run
    assert {h.chunk_id for h in hits} == {c["id"] for c in chunks}


def test_embedding_failure_marks_document_failed(client, monkeypatch):
    def broken(texts, client=None):
        raise EmbeddingError("Embedding request failed: rate limited")

    monkeypatch.setattr(embeddings, "embed_texts", broken)
    doc = upload_txt(client, "policy.txt", REFUNDS)

    doc = client.get(f"/documents/{doc['id']}").json()
    assert doc["status"] == "failed"
    assert "rate limited" in doc["error"]
    assert client.get(f"/documents/{doc['id']}/chunks").json() == []  # rolled back


def test_unreadable_pdf_marks_document_failed(client):
    response = client.post(
        "/documents/upload", files={"file": ("bad.pdf", b"%PDF-1.4 garbage", "application/pdf")}
    )
    doc = client.get(f"/documents/{response.json()['id']}").json()
    assert doc["status"] == "failed"
    assert doc["error"]
