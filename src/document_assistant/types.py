from dataclasses import dataclass


@dataclass(frozen=True)
class Passage:
    document: str
    page: int | None
    chunk_index: int
    text: str


@dataclass(frozen=True)
class Citation:
    document: str
    page: int | None
    excerpt: str


@dataclass(frozen=True)
class GroundedAnswer:
    answer: str
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class ScoredPassage:
    passage: Passage
    score: float
