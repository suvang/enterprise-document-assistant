from io import BytesIO
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from document_assistant.types import Passage

SUPPORTED_SUFFIXES = {".pdf", ".md", ".markdown", ".txt"}


def load_pages(name: str, data: bytes) -> list[tuple[int | None, str]]:
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported Document type: {suffix or name}")
    if suffix == ".pdf":
        return _pdf_pages(data)
    text = data.decode("utf-8")
    return [(None, text)]


def _pdf_pages(data: bytes) -> list[tuple[int | None, str]]:
    reader = PdfReader(BytesIO(data))
    return [
        (index, page.extract_text() or "")
        for index, page in enumerate(reader.pages, start=1)
    ]


def split_passages(
    name: str,
    pages: list[tuple[int | None, str]],
    splitter: RecursiveCharacterTextSplitter,
) -> list[Passage]:
    passages: list[Passage] = []
    chunk_index = 0
    for page, text in pages:
        for chunk in splitter.split_text(text):
            cleaned = chunk.strip()
            if not cleaned:
                continue
            passages.append(
                Passage(
                    document=name,
                    page=page,
                    chunk_index=chunk_index,
                    text=cleaned,
                )
            )
            chunk_index += 1
    return passages
