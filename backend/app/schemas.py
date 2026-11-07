from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_name: str
    content_type: str
    size_bytes: int
    page_count: int | None
    status: str
    error: str | None
    created_at: datetime


class PageTextOut(BaseModel):
    page_number: int
    text: str


class DocumentTextOut(BaseModel):
    document_id: int
    page_count: int
    pages: list[PageTextOut]
