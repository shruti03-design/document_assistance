"""Extract text from uploaded documents, keeping page numbers for later citations."""
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


class ExtractionError(Exception):
    pass


@dataclass
class PageText:
    page_number: int  # 1-based
    text: str


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)    # re-join words hyphenated across lines
    text = re.sub(r"[ \t]+", " ", text)              # collapse runs of spaces/tabs
    text = re.sub(r" *\n *", "\n", text)             # trim spaces around newlines
    text = re.sub(r"\n{3,}", "\n\n", text)           # keep paragraph breaks, drop extra blank lines
    return text.strip()


def extract_pdf(path: Path) -> list[PageText]:
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ExtractionError("PDF is password-protected")
        return [
            PageText(page_number=i, text=clean_text(page.extract_text() or ""))
            for i, page in enumerate(reader.pages, start=1)
        ]
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"Could not read PDF: {exc}") from exc


def extract_txt(path: Path) -> list[PageText]:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("latin-1")
    # A text file has no pages; treat it as a single page
    return [PageText(page_number=1, text=clean_text(text))]


def extract_pages(path: Path, content_type: str) -> list[PageText]:
    if content_type == "application/pdf":
        pages = extract_pdf(path)
    elif content_type == "text/plain":
        pages = extract_txt(path)
    else:
        raise ExtractionError(f"Unsupported content type: {content_type}")

    if not any(p.text for p in pages):
        raise ExtractionError(
            "No text could be extracted (the PDF may be scanned images, which need OCR)"
        )
    return pages
