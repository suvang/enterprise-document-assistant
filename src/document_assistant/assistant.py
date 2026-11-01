import threading

from langchain_text_splitters import RecursiveCharacterTextSplitter

from document_assistant.ingest import load_pages, split_passages
from document_assistant.types import Citation, DocumentSummary, GroundedAnswer

TOP_K = 4
MIN_SIMILARITY = 0.25
REFUSAL = "The documents do not contain an answer to that question."


class Assistant:
    def __init__(self, embedder, store, answerer, splitter=None) -> None:
        self.embedder = embedder
        self.store = store
        self.answerer = answerer
        self._splitter = splitter or RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )
        self._documents: dict[str, DocumentSummary] = {}
        self._lock = threading.Lock()

    def add_document(self, name: str, data: bytes) -> int:
        """Add a Document to the Corpus, replacing any earlier Document of the same name."""
        pages = load_pages(name, data)
        passages = split_passages(name, pages, self._splitter)
        if not passages:
            return 0
        vectors = self.embedder.embed([passage.text for passage in passages])
        page_numbers = {page for page, _ in pages if page is not None}
        with self._lock:
            self.store.remove(name)
            self.store.add(passages, vectors)
            self._documents[name] = DocumentSummary(
                name=name,
                passages=len(passages),
                pages=len(page_numbers) if page_numbers else None,
            )
        return len(passages)

    def documents(self) -> tuple[DocumentSummary, ...]:
        """Documents added to the Corpus by this service, oldest first."""
        with self._lock:
            return tuple(self._documents.values())

    def remove_document(self, name: str) -> bool:
        with self._lock:
            if name not in self._documents:
                return False
            self.store.remove(name)
            del self._documents[name]
        return True

    def ask(self, question: str) -> GroundedAnswer:
        if not question.strip():
            raise ValueError("Question must not be blank")
        vector = self.embedder.embed([question])[0]
        scored = self.store.search(vector, TOP_K)
        relevant = tuple(item for item in scored if item.score >= MIN_SIMILARITY)
        if not relevant:
            return GroundedAnswer(answer=REFUSAL, citations=())
        answer = self.answerer.answer(question, tuple(item.passage for item in relevant))
        citations = tuple(
            Citation(
                document=item.passage.document,
                page=item.passage.page,
                excerpt=item.passage.text,
                score=round(item.score, 4),
            )
            for item in relevant
        )
        return GroundedAnswer(answer=answer, citations=citations)
