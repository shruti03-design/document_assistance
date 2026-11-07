from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_index: int
    page_number: int
    text: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[int] | None = None  # limit the search to these documents
    top_k: int | None = Field(default=None, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value


class SourceOut(BaseModel):
    chunk_id: int
    document_id: int
    document_name: str
    page_number: int
    score: float
    text: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
