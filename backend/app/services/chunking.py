"""Split extracted pages into overlapping chunks suitable for embedding.

Chunks never cross page boundaries, so every chunk maps to exactly one page number
(needed for citations). Within a page, text is split on the most natural boundary
available: paragraphs, then lines, then sentences, then words, then raw characters.
"""
from dataclasses import dataclass

from app.services.extraction import PageText

SEPARATORS = ["\n\n", "\n", ". ", " "]


@dataclass
class TextChunk:
    chunk_index: int   # 0-based position within the document
    page_number: int
    text: str


def _split_into_pieces(text: str, max_size: int, separators: list[str]) -> list[str]:
    """Break text into pieces no longer than max_size, preferring earlier separators."""
    if len(text) <= max_size:
        return [text]
    if not separators:
        return [text[i:i + max_size] for i in range(0, len(text), max_size)]

    sep, rest = separators[0], separators[1:]
    parts = text.split(sep)
    pieces: list[str] = []
    for i, part in enumerate(parts):
        if i < len(parts) - 1:
            part += sep  # keep the separator so joined text reads naturally
        if not part:
            continue
        if len(part) <= max_size:
            pieces.append(part)
        else:
            pieces.extend(_split_into_pieces(part, max_size, rest))
    return pieces


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Greedily merge pieces into chunks of up to chunk_size characters with overlap."""
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for piece in _split_into_pieces(text, chunk_size, SEPARATORS):
        if current and current_len + len(piece) > chunk_size:
            chunks.append("".join(current).strip())
            # Keep trailing pieces as overlap, as long as they fit within the overlap
            # budget and still leave room for the new piece.
            while current and (
                current_len > chunk_overlap or current_len + len(piece) > chunk_size
            ):
                current_len -= len(current.pop(0))
        current.append(piece)
        current_len += len(piece)

    if current:
        chunks.append("".join(current).strip())
    return [c for c in chunks if c]


def chunk_pages(pages: list[PageText], chunk_size: int, chunk_overlap: int) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page in pages:
        for text in split_text(page.text, chunk_size, chunk_overlap):
            chunks.append(TextChunk(chunk_index=len(chunks), page_number=page.page_number, text=text))
    return chunks
