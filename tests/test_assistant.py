"""Behavior of the assistant service: add a Document, ask a Question."""

from document_assistant.answerers import OpenAIAnswerer, PassageAnswerer
from document_assistant.assistant import REFUSAL, Assistant
from document_assistant.factory import build_assistant
from document_assistant.store import InMemoryVectorStore
from document_assistant.types import Passage
from fpdf import FPDF


class MapEmbedder:
    def __init__(self, vectors: dict[str, list[float]], default: list[float] | None = None):
        self.vectors = vectors
        self.default = default or [0.0, 1.0]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.vectors.get(text, self.default) for text in texts]


class RecordingAnswerer:
    def __init__(self, text: str = "15 vacation days") -> None:
        self.text = text
        self.calls: list[tuple[str, tuple[Passage, ...]]] = []

    def answer(self, question: str, passages: tuple[Passage, ...]) -> str:
        self.calls.append((question, passages))
        return self.text


def assistant_with(embedder, answerer) -> Assistant:
    return Assistant(embedder=embedder, store=InMemoryVectorStore(), answerer=answerer)


def test_ask_returns_grounded_answer_and_citation():
    embedder = MapEmbedder(
        {
            "Employees receive 15 vacation days per year.": [1.0, 0.0],
            "How many vacation days do employees receive?": [1.0, 0.0],
        }
    )
    answerer = RecordingAnswerer("15 vacation days")
    assistant = assistant_with(embedder, answerer)

    added = assistant.add_document(
        "handbook.md",
        b"Employees receive 15 vacation days per year.",
    )

    result = assistant.ask("How many vacation days do employees receive?")

    assert added == 1
    assert result.answer == "15 vacation days"
    assert len(result.citations) == 1
    citation = result.citations[0]
    assert citation.document == "handbook.md"
    assert citation.page is None
    assert citation.excerpt == "Employees receive 15 vacation days per year."
    assert answerer.calls[0][1][0].text == "Employees receive 15 vacation days per year."


def test_ask_returns_at_most_four_citations():
    vectors = {f"policy fact {i}": [1.0, 0.0] for i in range(5)}
    vectors["Which policy facts apply?"] = [1.0, 0.0]
    embedder = MapEmbedder(vectors)
    answerer = RecordingAnswerer("several facts")
    assistant = assistant_with(embedder, answerer)
    for i in range(5):
        assistant.add_document(f"policy-{i}.txt", f"policy fact {i}".encode())

    result = assistant.ask("Which policy facts apply?")

    assert len(result.citations) == 4
    assert len(answerer.calls[0][1]) == 4


def test_long_manual_cites_the_passage_that_contains_the_fact():
    filler = "Background office notes. " * 80
    body = filler + "Employees receive 15 vacation days per year."
    embedder = MapEmbedder({}, default=[0.0, 1.0])
    embedder.embed = lambda texts: [  # type: ignore[method-assign]
        [1.0, 0.0] if "vacation days" in text else [0.0, 1.0] for text in texts
    ]
    answerer = RecordingAnswerer("15 vacation days")
    assistant = assistant_with(embedder, answerer)

    added = assistant.add_document("handbook.md", body.encode())
    result = assistant.ask("How many vacation days?")

    assert added >= 2
    assert result.citations[0].document == "handbook.md"
    assert "15 vacation days" in result.citations[0].excerpt
    assert "15 vacation days" in answerer.calls[0][1][0].text


def test_pdf_citation_includes_the_page():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="Employees receive 15 vacation days per year.")
    data = bytes(pdf.output())
    embedder = MapEmbedder({})
    embedder.embed = lambda texts: [[1.0, 0.0] for _ in texts]  # type: ignore[method-assign]
    assistant = assistant_with(embedder, RecordingAnswerer("15 vacation days"))

    added = assistant.add_document("leave.pdf", data)
    result = assistant.ask("How many vacation days?")

    assert added == 1
    assert result.citations[0].document == "leave.pdf"
    assert result.citations[0].page == 1
    assert "15 vacation days" in result.citations[0].excerpt


def test_empty_document_adds_nothing():
    assistant = assistant_with(MapEmbedder({}), RecordingAnswerer())
    assert assistant.add_document("empty.txt", b"   \n") == 0


def test_unsupported_document_is_rejected():
    assistant = assistant_with(MapEmbedder({}), RecordingAnswerer())
    try:
        assistant.add_document("notes.docx", b"hello")
    except ValueError as error:
        assert "unsupported" in str(error).lower()
    else:
        raise AssertionError("expected rejection")
    result = assistant.ask("hello")
    assert result.answer == REFUSAL


def test_empty_corpus_refuses_without_calling_the_answerer():
    answerer = RecordingAnswerer()
    assistant = assistant_with(MapEmbedder({"What is the firewall rule?": [1.0, 0.0]}), answerer)

    result = assistant.ask("What is the firewall rule?")

    assert result.answer == REFUSAL
    assert result.citations == ()
    assert answerer.calls == []


def test_unrelated_question_refuses():
    embedder = MapEmbedder(
        {
            "The office closes at 6pm.": [1.0, 0.0],
            "What is the parental leave policy?": [0.0, 1.0],
        }
    )
    answerer = RecordingAnswerer()
    assistant = assistant_with(embedder, answerer)
    assistant.add_document("hours.txt", b"The office closes at 6pm.")

    result = assistant.ask("What is the parental leave policy?")

    assert result.answer == REFUSAL
    assert result.citations == ()
    assert answerer.calls == []


def test_blank_question_is_rejected():
    assistant = assistant_with(MapEmbedder({}), RecordingAnswerer())
    try:
        assistant.ask("   ")
    except ValueError as error:
        assert "blank" in str(error).lower()
    else:
        raise AssertionError("expected rejection")


class ScriptedChat:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages = messages
        return "Use 15 days"


def test_model_prompt_contains_only_the_question_and_passages():
    chat = ScriptedChat()
    answerer = OpenAIAnswerer(chat)
    passages = (
        Passage(document="handbook.md", page=None, chunk_index=0, text="Employees receive 15 vacation days per year."),
    )

    answer = answerer.answer("How many vacation days?", passages)

    assert answer == "Use 15 days"
    joined = "\n".join(message["content"] for message in chat.messages)
    assert "How many vacation days?" in joined
    assert "Employees receive 15 vacation days per year." in joined
    assert "only" in joined.lower()


def test_passage_answerer_returns_the_first_passage():
    answerer = PassageAnswerer()
    passages = (
        Passage(document="handbook.md", page=None, chunk_index=0, text="Employees receive 15 vacation days per year."),
        Passage(document="other.md", page=None, chunk_index=1, text="Unused."),
    )
    assert answerer.answer("vacation", passages) == "Employees receive 15 vacation days per year."


def test_missing_pinecone_settings_use_memory():
    assistant = build_assistant({})
    assert isinstance(assistant.store, InMemoryVectorStore)


def test_both_pinecone_settings_use_pinecone_adapter():
    created: dict[str, str] = {}

    def factory(api_key: str, index_name: str, embedder=None):
        created["api_key"] = api_key
        created["index_name"] = index_name
        created["has_embedder"] = embedder is not None
        return InMemoryVectorStore()

    build_assistant(
        {"PINECONE_API_KEY": "pc-key", "PINECONE_INDEX": "manuals"},
        pinecone_store=factory,
    )
    assert created["api_key"] == "pc-key"
    assert created["index_name"] == "manuals"
    assert created["has_embedder"] is True


def test_one_pinecone_setting_stays_on_memory():
    assistant = build_assistant({"PINECONE_API_KEY": "pc-key"})
    assert isinstance(assistant.store, InMemoryVectorStore)
