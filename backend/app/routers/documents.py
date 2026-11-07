from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage
from app.config import settings
from app.db import get_db
from app.models import Document, DocumentStatus
from app.schemas import DocumentOut, DocumentTextOut
from app.services.extraction import ExtractionError, extract_pages

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, db: Session = Depends(get_db)):
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension or 'none'}'. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit")
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")
    if extension == ".pdf" and not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File is not a valid PDF")

    stored_name = storage.save_file(data, extension)
    document = Document(
        original_name=filename,
        stored_name=stored_name,
        content_type=ALLOWED_TYPES[extension],
        size_bytes=len(data),
    )

    try:
        pages = extract_pages(storage.file_path(stored_name), document.content_type)
        document.page_count = len(pages)
    except ExtractionError as exc:
        document.status = DocumentStatus.FAILED
        document.error = str(exc)

    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.scalars(select(Document).order_by(Document.created_at.desc())).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id}/text", response_model=DocumentTextOut)
def get_document_text(document_id: int, db: Session = Depends(get_db)):
    """Return the extracted text page by page (useful for checking extraction quality)."""
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        pages = extract_pages(storage.file_path(document.stored_name), document.content_type)
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return DocumentTextOut(
        document_id=document.id,
        page_count=len(pages),
        pages=[{"page_number": p.page_number, "text": p.text} for p in pages],
    )
