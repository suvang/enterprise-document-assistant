import os
from collections.abc import Mapping

from document_assistant.answerers import LangChainChat, OpenAIAnswerer, PassageAnswerer
from document_assistant.assistant import Assistant
from document_assistant.embedders import HashEmbedder, OpenAIEmbedder
from document_assistant.store import InMemoryVectorStore


def build_pinecone_store(api_key: str, index_name: str, embedder=None):
    from langchain_pinecone import PineconeVectorStore
    from pinecone import Pinecone

    index = Pinecone(api_key=api_key).Index(index_name)
    embedding = _langchain_embedding(embedder)
    store = PineconeVectorStore(index=index, embedding=embedding, text_key="text")
    return PineconePassageStore(store)


def _langchain_embedding(embedder):
    from langchain_core.embeddings import Embeddings

    class Adapter(Embeddings):
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return embedder.embed(list(texts))

        def embed_query(self, text: str) -> list[float]:
            return embedder.embed([text])[0]

    return Adapter()


def _document_prefix(document: str) -> str:
    import hashlib

    return hashlib.sha1(document.encode()).hexdigest()[:16] + "#"


def _passage_id(document: str, chunk_index: int) -> str:
    return f"{_document_prefix(document)}{chunk_index}"


class PineconePassageStore:
    """Adapts a LangChain Pinecone store to the Passage port."""

    def __init__(self, store) -> None:
        self._store = store

    def add(self, passages, vectors) -> None:
        rows = []
        for passage, vector in zip(passages, vectors):
            metadata = {
                "text": passage.text,
                "document": passage.document,
                "chunk_index": passage.chunk_index,
            }
            if passage.page is not None:
                metadata["page"] = passage.page
            rows.append((_passage_id(passage.document, passage.chunk_index), vector, metadata))
        for start in range(0, len(rows), 100):
            self._store.index.upsert(vectors=rows[start : start + 100])

    def remove(self, document: str) -> None:
        """Delete a Document's Passages. IDs share a per-Document prefix."""
        index = self._store.index
        prefix = _document_prefix(document)
        try:
            for ids in index.list(prefix=prefix):
                if ids:
                    index.delete(ids=list(ids))
        except Exception:
            # Pod-based indexes cannot list IDs; they support metadata filters instead.
            try:
                index.delete(filter={"document": {"$eq": document}})
            except Exception:
                pass

    def search(self, vector, k: int):
        from document_assistant.types import Passage, ScoredPassage

        pairs = self._store.similarity_search_by_vector_with_score(vector, k=k)
        scored = []
        for document, score in pairs:
            metadata = document.metadata
            page = metadata.get("page")
            scored.append(
                ScoredPassage(
                    passage=Passage(
                        document=str(metadata.get("document", "")),
                        # Pinecone returns numeric metadata as floats.
                        page=int(page) if isinstance(page, (int, float)) else None,
                        chunk_index=int(metadata.get("chunk_index", 0)),
                        text=document.page_content,
                    ),
                    score=float(score),
                )
            )
        return scored


def build_assistant(
    env: Mapping[str, str] | None = None,
    pinecone_store=build_pinecone_store,
) -> Assistant:
    settings: Mapping[str, str]
    if env is None:
        from dotenv import load_dotenv

        load_dotenv()
        settings = os.environ
    else:
        settings = env
    api_key = settings.get("PINECONE_API_KEY") or ""
    index_name = settings.get("PINECONE_INDEX") or ""
    openai_key = settings.get("OPENAI_API_KEY") or ""
    embedder: HashEmbedder | OpenAIEmbedder
    answerer: PassageAnswerer | OpenAIAnswerer
    if openai_key:
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings

        embedder = OpenAIEmbedder(
            OpenAIEmbeddings(model="text-embedding-3-small", api_key=openai_key)  # type: ignore[arg-type]
        )
        answerer = OpenAIAnswerer(
            LangChainChat(ChatOpenAI(model="gpt-4o-mini", api_key=openai_key))  # type: ignore[arg-type]
        )
    else:
        embedder = HashEmbedder()
        answerer = PassageAnswerer()

    if api_key and index_name:
        store = pinecone_store(api_key, index_name, embedder)
    else:
        store = InMemoryVectorStore()
    return Assistant(embedder=embedder, store=store, answerer=answerer)
