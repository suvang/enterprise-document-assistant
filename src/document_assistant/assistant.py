from langchain_text_splitters import RecursiveCharacterTextSplitter

from document_assistant.ingest import load_pages, split_passages
from document_assistant.types import Citation, GroundedAnswer

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

    def add_document(self, name: str, data: bytes) -> int:
        passages = split_passages(name, load_pages(name, data), self._splitter)
        if not passages:
            return 0
        vectors = self.embedder.embed([passage.text for passage in passages])
        self.store.add(passages, vectors)
        return len(passages)

    def ask(self, question: str) -> GroundedAnswer:
        if not question.strip():
            raise ValueError("Question must not be blank")
        vector = self.embedder.embed([question])[0]
        scored = self.store.search(vector, TOP_K)
        relevant = tuple(
            item.passage for item in scored if item.score >= MIN_SIMILARITY
        )
        if not relevant:
            return GroundedAnswer(answer=REFUSAL, citations=())
        answer = self.answerer.answer(question, relevant)
        citations = tuple(
            Citation(document=passage.document, page=passage.page, excerpt=passage.text)
            for passage in relevant
        )
        return GroundedAnswer(answer=answer, citations=citations)
