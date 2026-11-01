from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from document_assistant.answerers import PassageAnswerer
from document_assistant.assistant import Assistant
from document_assistant.factory import build_assistant
from document_assistant.store import InMemoryVectorStore

PAGE = Path(__file__).parent / "static" / "index.html"
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024


class QuestionBody(BaseModel):
    question: str


def describe(service: Assistant) -> dict[str, str]:
    """Which adapters are active, so a client can explain what kind of answer to expect."""
    return {
        "store": "memory" if isinstance(service.store, InMemoryVectorStore) else "pinecone",
        "answerer": "passage" if isinstance(service.answerer, PassageAnswerer) else "openai",
    }


def create_app(assistant: Assistant | None = None) -> FastAPI:
    app = FastAPI(title="Enterprise Document Assistant")
    service = assistant or build_assistant()

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(PAGE)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", **describe(service)}

    @app.get("/documents")
    def list_documents() -> list[dict]:
        return [
            {"document": item.name, "passages": item.passages, "pages": item.pages}
            for item in service.documents()
        ]

    @app.post("/documents")
    async def add_document(file: UploadFile = File(...)) -> dict:
        data = await file.read()
        if len(data) > MAX_DOCUMENT_BYTES:
            raise HTTPException(status_code=413, detail="The Document is larger than 25 MB.")
        name = Path(file.filename or "document.txt").name
        replaced = any(item.name == name for item in service.documents())
        try:
            passages = service.add_document(name, data)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"document": name, "passages": passages, "replaced": replaced}

    @app.delete("/documents/{name:path}")
    def remove_document(name: str) -> dict[str, str]:
        if not service.remove_document(name):
            raise HTTPException(status_code=404, detail="No Document with that name.")
        return {"removed": name}

    @app.post("/questions")
    def ask(body: QuestionBody) -> dict:
        try:
            result = service.ask(body.question)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {
            "answer": result.answer,
            "citations": [
                {
                    "document": citation.document,
                    "page": citation.page,
                    "excerpt": citation.excerpt,
                    "score": citation.score,
                }
                for citation in result.citations
            ],
        }

    return app
