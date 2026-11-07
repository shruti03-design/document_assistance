"""Generate embeddings with the OpenAI API.

Run `python -m app.services.embeddings "some text"` from backend/ to check your API key.
"""
from functools import lru_cache

import openai
from openai import OpenAI

from app.config import settings


class EmbeddingError(Exception):
    pass


@lru_cache
def get_client() -> OpenAI:
    if not settings.openai_api_key or settings.openai_api_key.startswith("sk-your"):
        raise EmbeddingError("OPENAI_API_KEY is not set in backend/.env")
    # The SDK retries rate limits and transient errors with backoff
    return OpenAI(api_key=settings.openai_api_key, max_retries=3, timeout=60)


def embed_texts(texts: list[str], client: OpenAI | None = None) -> list[list[float]]:
    """Embed many texts, sending them to the API in batches. Output order matches input."""
    if not texts:
        return []
    client = client or get_client()
    vectors: list[list[float]] = []
    batch_size = settings.embedding_batch_size

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        try:
            response = client.embeddings.create(
                model=settings.embedding_model,
                input=batch,
                dimensions=settings.embedding_dimensions,
            )
        except openai.OpenAIError as exc:
            raise EmbeddingError(f"Embedding request failed: {exc}") from exc
        # Sort by index to guarantee order matches the input batch
        vectors.extend(item.embedding for item in sorted(response.data, key=lambda d: d.index))

    if len(vectors) != len(texts):
        raise EmbeddingError(f"Expected {len(texts)} embeddings, got {len(vectors)}")
    return vectors


def embed_query(text: str, client: OpenAI | None = None) -> list[float]:
    return embed_texts([text], client=client)[0]


if __name__ == "__main__":
    import sys

    sample = " ".join(sys.argv[1:]) or "Hello, world"
    vector = embed_query(sample)
    print(f"model={settings.embedding_model} dimensions={len(vector)} first values={vector[:5]}")
