from io import BytesIO
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from document_assistant.types import Passage

SUPPORTED_SUFFIXES = {".pdf", ".md", ".markdown", ".txt"}


def load_pages(name: str, data: bytes) -> list[tuple[int | None, str]]:
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported Document type: {suffix or name}")
    if suffix == ".pdf":
        return _pdf_pages(data)
    return [(None, _decode_text(data))]


def _decode_text(data: bytes) -> str:
    # utf-8-sig strips a byte-order mark; cp1252 covers most exports from
    # older Windows tools. Anything else is decoded leniently rather than failing.
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _pdf_pages(data: bytes) -> list[tuple[int | None, str]]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(BytesIO(data))
        return [
            (index, page.extract_text() or "")
            for index, page in enumerate(reader.pages, start=1)
        ]
    except (PdfReadError, ValueError, KeyError, TypeError) as error:
        raise ValueError("The PDF could not be read. It may be damaged or encrypted.") from error


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
