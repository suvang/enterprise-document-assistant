import math

from document_assistant.types import Passage, ScoredPassage


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._items: list[tuple[Passage, list[float]]] = []

    def add(self, passages: list[Passage], vectors: list[list[float]]) -> None:
        self._items.extend(zip(passages, vectors))

    def search(self, vector: list[float], k: int) -> list[ScoredPassage]:
        scored = [
            ScoredPassage(passage, cosine(vector, stored))
            for passage, stored in self._items
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:k]
