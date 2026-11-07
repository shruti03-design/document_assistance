"""Test setup: SQLite + in-memory Qdrant + temp upload dir, so tests need no Docker or API key.

Environment variables must be set before the app modules are imported.
"""
import hashlib
import math
import os
import re
import tempfile

_tmp = tempfile.mkdtemp(prefix="docassist-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["QDRANT_URL"] = ":memory:"
os.environ["OPENAI_API_KEY"] = "test-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import embeddings, vector_store  # noqa: E402


def fake_vector(text: str) -> list[float]:
    """Bag-of-words hashing: texts sharing words get similar vectors (enough to test search)."""
    vec = [0.0] * settings.embedding_dimensions
    for word in re.findall(r"\w+", text.lower()):
        vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % len(vec)] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


@pytest.fixture
def fake_embeddings(monkeypatch):
    calls = []

    def embed_texts(texts, client=None):
        calls.append(list(texts))
        return [fake_vector(t) for t in texts]

    monkeypatch.setattr(embeddings, "embed_texts", embed_texts)
    return calls


@pytest.fixture
def client(fake_embeddings):
    # Fresh database and Qdrant collection for every test
    Base.metadata.drop_all(bind=engine)
    vector_store.get_client.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
