from types import SimpleNamespace

import openai
import pytest

from app.config import settings
from app.services.embeddings import EmbeddingError, embed_query, embed_texts


class FakeEmbeddings:
    """Stands in for client.embeddings; returns a vector encoding each input's identity."""

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def create(self, model, input, dimensions):
        self.calls.append(list(input))
        if self.fail:
            raise openai.APIConnectionError(request=None)
        data = [
            SimpleNamespace(index=i, embedding=[float(len(text))] * dimensions)
            for i, text in enumerate(input)
        ]
        return SimpleNamespace(data=list(reversed(data)))  # out of order on purpose


def fake_client(fail=False):
    return SimpleNamespace(embeddings=FakeEmbeddings(fail))


def test_batches_and_preserves_order(monkeypatch):
    monkeypatch.setattr(settings, "embedding_batch_size", 2)
    client = fake_client()
    texts = ["a", "bb", "ccc", "dddd", "eeeee"]

    vectors = embed_texts(texts, client=client)

    assert [len(b) for b in client.embeddings.calls] == [2, 2, 1]
    assert [v[0] for v in vectors] == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert all(len(v) == settings.embedding_dimensions for v in vectors)


def test_empty_input_makes_no_calls():
    client = fake_client()
    assert embed_texts([], client=client) == []
    assert client.embeddings.calls == []


def test_embed_query_returns_single_vector():
    assert embed_query("hello", client=fake_client())[0] == 5.0


def test_api_errors_are_wrapped():
    with pytest.raises(EmbeddingError):
        embed_texts(["x"], client=fake_client(fail=True))
