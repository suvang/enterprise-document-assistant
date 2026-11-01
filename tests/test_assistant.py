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


def test_home_page_offers_upload_and_ask():
    from fastapi.testclient import TestClient

    from document_assistant.api import create_app

    client = TestClient(create_app(assistant_with(MapEmbedder({}), RecordingAnswerer())))
    response = client.get("/")

    assert response.status_code == 200
    assert "Enterprise Document Assistant" in response.text
    assert 'id="upload"' in response.text
    assert 'id="ask"' in response.text


def test_documents_lists_what_was_added():
    assistant = assistant_with(MapEmbedder({}), RecordingAnswerer())
    assistant.add_document("handbook.md", b"Employees receive 15 vacation days per year.")
    assistant.add_document("empty.txt", b"   ")

    listed = assistant.documents()

    assert [(item.name, item.passages, item.pages) for item in listed] == [("handbook.md", 1, None)]


def test_adding_a_document_again_replaces_its_passages():
    embedder = MapEmbedder({}, default=[1.0, 0.0])
    assistant = assistant_with(embedder, RecordingAnswerer("ok"))
    assistant.add_document("handbook.md", b"Employees receive 10 vacation days per year.")
    assistant.add_document("handbook.md", b"Employees receive 15 vacation days per year.")

    result = assistant.ask("How many vacation days?")

    assert [citation.excerpt for citation in result.citations] == [
        "Employees receive 15 vacation days per year."
    ]
    assert len(assistant.documents()) == 1


def test_removed_document_no_longer_answers():
    embedder = MapEmbedder({}, default=[1.0, 0.0])
    assistant = assistant_with(embedder, RecordingAnswerer())
    assistant.add_document("handbook.md", b"Employees receive 15 vacation days per year.")

    assert assistant.remove_document("handbook.md") is True
    assert assistant.remove_document("handbook.md") is False
    result = assistant.ask("How many vacation days?")

    assert result.answer == REFUSAL
    assert assistant.documents() == ()


def test_citation_carries_relevance_score():
    embedder = MapEmbedder({}, default=[1.0, 0.0])
    assistant = assistant_with(embedder, RecordingAnswerer())
    assistant.add_document("handbook.md", b"Employees receive 15 vacation days per year.")

    result = assistant.ask("How many vacation days?")

    assert result.citations[0].score == 1.0


def test_non_utf8_text_document_is_added():
    embedder = MapEmbedder({}, default=[1.0, 0.0])
    assistant = assistant_with(embedder, RecordingAnswerer())

    added = assistant.add_document("cafe.txt", "Café opens at 8am.".encode("cp1252"))
    result = assistant.ask("When does the cafe open?")

    assert added == 1
    assert result.citations[0].excerpt == "Café opens at 8am."


def test_damaged_pdf_is_rejected():
    assistant = assistant_with(MapEmbedder({}), RecordingAnswerer())
    try:
        assistant.add_document("broken.pdf", b"not really a pdf")
    except ValueError as error:
        assert "pdf" in str(error).lower()
    else:
        raise AssertionError("expected rejection")


def test_local_embedder_matches_the_sample_question_and_refuses_unrelated_ones():
    from document_assistant.embedders import HashEmbedder

    assistant = assistant_with(HashEmbedder(), PassageAnswerer())
    assistant.add_document(
        "vacation-policy.md",
        b"# Leave policy\n\nEmployees receive 15 vacation days per year.\nThe office closes at 6pm.",
    )

    found = assistant.ask("How many vacation days do employees receive?")
    unrelated = assistant.ask("What is the firewall rule for the VPN?")

    assert found.citations[0].document == "vacation-policy.md"
    assert "15 vacation days" in found.answer
    assert unrelated.answer == REFUSAL


def test_model_prompt_numbers_the_passages_for_citation():
    chat = ScriptedChat()
    passages = (
        Passage(document="handbook.md", page=None, chunk_index=0, text="First fact."),
        Passage(document="leave.pdf", page=3, chunk_index=4, text="Second fact."),
    )

    OpenAIAnswerer(chat).answer("Which facts?", passages)

    user = chat.messages[-1]["content"]
    assert "[1] (handbook.md)\nFirst fact." in user
    assert "[2] (leave.pdf, page 3)\nSecond fact." in user


def test_http_lists_removes_and_reports_mode():
    from fastapi.testclient import TestClient

    from document_assistant.api import create_app

    embedder = MapEmbedder({}, default=[1.0, 0.0])
    client = TestClient(create_app(assistant_with(embedder, PassageAnswerer())))

    added = client.post("/documents", files={"file": ("handbook.md", b"Employees receive 15 vacation days.")})
    again = client.post("/documents", files={"file": ("handbook.md", b"Employees receive 15 vacation days.")})
    listed = client.get("/documents").json()
    asked = client.post("/questions", json={"question": "vacation?"}).json()
    removed = client.delete("/documents/handbook.md")
    missing = client.delete("/documents/handbook.md")
    health = client.get("/health").json()

    assert added.json() == {"document": "handbook.md", "passages": 1, "replaced": False}
    assert again.json()["replaced"] is True
    assert listed == [{"document": "handbook.md", "passages": 1, "pages": None}]
    assert asked["citations"][0]["score"] == 1.0
    assert removed.status_code == 200
    assert missing.status_code == 404
    assert health == {"status": "ok", "store": "memory", "answerer": "passage"}
    assert client.get("/documents").json() == []
