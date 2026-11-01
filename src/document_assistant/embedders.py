import hashlib
import re

_TOKEN = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")

# Common words carry no topic signal; dropping them keeps unrelated Questions
# from looking similar to every Passage in the local stand-in.
_STOPWORDS = frozenset(
    """
    a an and are as at be been but by can could did do does for from had has
    have how i if in into is it its may me my of on or our should so than that
    the their them then there these they this to was we were what when where
    which who why will with would you your about any all also many much must
    """.split()
)


def tokenize(text: str) -> list[str]:
    tokens = []
    for token in _TOKEN.findall(text.lower()):
        if token in _STOPWORDS:
            continue
        # Light stemming so "days" matches "day" and "policies" matches "policy".
        if len(token) > 4 and token.endswith("ies"):
            token = token[:-3] + "y"
        elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        tokens.append(token)
    return tokens


class HashEmbedder:
    """Local stand-in so a run without an OpenAI key can still retrieve Passages."""

    def __init__(self, dimensions: int = 512) -> None:
        self._dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:2], "big") % self._dimensions
            vector[index] += 1.0
        return vector


class OpenAIEmbedder:
    def __init__(self, embeddings) -> None:
        self._embeddings = embeddings

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings.embed_documents(texts)
