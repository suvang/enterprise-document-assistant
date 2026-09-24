import hashlib


class HashEmbedder:
    """Local stand-in so a run without an OpenAI key can still retrieve Passages."""

    def __init__(self, dimensions: int = 256) -> None:
        self._dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:2], "big") % self._dimensions
            vector[index] += 1.0
        return vector


class OpenAIEmbedder:
    def __init__(self, embeddings) -> None:
        self._embeddings = embeddings

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings.embed_documents(texts)
