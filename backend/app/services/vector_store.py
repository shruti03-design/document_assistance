"""Store and search chunk embeddings in Qdrant.

Each Qdrant point uses the MySQL chunk id as its id, and carries the chunk text and
metadata (document id, page number, ...) as payload so search results are self-contained.
Set QDRANT_URL=":memory:" to run an in-process Qdrant (handy for tests without Docker).
"""
from dataclasses import dataclass
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import settings


@dataclass
class ChunkPoint:
    chunk_id: int
    vector: list[float]
    document_id: int
    document_name: str
    chunk_index: int
    page_number: int
    text: str


@dataclass
class SearchHit:
    chunk_id: int
    score: float
    document_id: int
    document_name: str
    page_number: int
    text: str


@lru_cache
def get_client() -> QdrantClient:
    if settings.qdrant_url == ":memory:":
        client = QdrantClient(location=":memory:")
    else:
        client = QdrantClient(url=settings.qdrant_url)
    _ensure_collection(client)
    return client


def _ensure_collection(client: QdrantClient) -> None:
    name = settings.qdrant_collection
    if client.collection_exists(name):
        return
    client.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(
            size=settings.embedding_dimensions, distance=qm.Distance.COSINE
        ),
    )
    if settings.qdrant_url == ":memory:":
        return  # payload indexes only apply to a Qdrant server
    # Index document_id so searches can be filtered to specific documents quickly
    client.create_payload_index(
        collection_name=name,
        field_name="document_id",
        field_schema=qm.PayloadSchemaType.INTEGER,
    )


def upsert_chunks(points: list[ChunkPoint]) -> None:
    if not points:
        return
    get_client().upsert(
        collection_name=settings.qdrant_collection,
        points=[
            qm.PointStruct(
                id=p.chunk_id,
                vector=p.vector,
                payload={
                    "chunk_id": p.chunk_id,
                    "document_id": p.document_id,
                    "document_name": p.document_name,
                    "chunk_index": p.chunk_index,
                    "page_number": p.page_number,
                    "text": p.text,
                },
            )
            for p in points
        ],
        wait=True,
    )


def _document_filter(document_ids: list[int]) -> qm.Filter:
    return qm.Filter(
        must=[qm.FieldCondition(key="document_id", match=qm.MatchAny(any=document_ids))]
    )


def delete_document_vectors(document_id: int) -> None:
    get_client().delete(
        collection_name=settings.qdrant_collection,
        points_selector=qm.FilterSelector(filter=_document_filter([document_id])),
        wait=True,
    )


def search(
    query_vector: list[float], limit: int = 5, document_ids: list[int] | None = None
) -> list[SearchHit]:
    response = get_client().query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=limit,
        query_filter=_document_filter(document_ids) if document_ids else None,
        with_payload=True,
    )
    return [
        SearchHit(
            chunk_id=point.payload["chunk_id"],
            score=point.score,
            document_id=point.payload["document_id"],
            document_name=point.payload["document_name"],
            page_number=point.payload["page_number"],
            text=point.payload["text"],
        )
        for point in response.points
    ]
