"""Indexing pipeline: extract text -> chunk -> embed -> store vectors.

Safe to run again on the same document (re-indexing): old chunks and vectors are replaced.
"""
import logging

from sqlalchemy.orm import Session

from app import storage
from app.config import settings
from app.db import SessionLocal
from app.models import Chunk, Document, DocumentStatus
from app.services import embeddings, vector_store
from app.services.chunking import chunk_pages
from app.services.embeddings import EmbeddingError
from app.services.extraction import ExtractionError, extract_pages

logger = logging.getLogger(__name__)


def index_document(db: Session, document: Document) -> None:
    document.status = DocumentStatus.PROCESSING
    document.error = None
    db.commit()

    try:
        pages = extract_pages(storage.file_path(document.stored_name), document.content_type)
        text_chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)

        # Replace any previous chunks, then flush so the new chunks get their ids
        document.page_count = len(pages)
        document.chunks = [
            Chunk(chunk_index=c.chunk_index, page_number=c.page_number, text=c.text)
            for c in text_chunks
        ]
        db.flush()

        vectors = embeddings.embed_texts([c.text for c in document.chunks])

        vector_store.delete_document_vectors(document.id)
        vector_store.upsert_chunks(
            [
                vector_store.ChunkPoint(
                    chunk_id=chunk.id,
                    vector=vector,
                    document_id=document.id,
                    document_name=document.original_name,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    text=chunk.text,
                )
                for chunk, vector in zip(document.chunks, vectors)
            ]
        )

        document.status = DocumentStatus.READY
        db.commit()
        logger.info("Indexed document %s (%s chunks)", document.id, len(document.chunks))

    except (ExtractionError, EmbeddingError) as exc:
        _mark_failed(db, document, str(exc))
    except Exception as exc:
        logger.exception("Unexpected error indexing document %s", document.id)
        _mark_failed(db, document, f"Unexpected error: {exc}")


def _mark_failed(db: Session, document: Document, message: str) -> None:
    db.rollback()
    document.status = DocumentStatus.FAILED
    document.error = message[:1000]
    db.commit()


def index_document_in_background(document_id: int) -> None:
    """Entry point for FastAPI BackgroundTasks; opens its own DB session."""
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is not None:
            index_document(db, document)
    finally:
        db.close()
