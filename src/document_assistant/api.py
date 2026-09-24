from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from document_assistant.assistant import Assistant
from document_assistant.factory import build_assistant


class QuestionBody(BaseModel):
    question: str


def create_app(assistant: Assistant | None = None) -> FastAPI:
    app = FastAPI(title="Enterprise Document Assistant")
    service = assistant or build_assistant()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/documents")
    async def add_document(file: UploadFile = File(...)) -> dict[str, str | int]:
        data = await file.read()
        name = file.filename or "document.txt"
        try:
            passages = service.add_document(name, data)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"document": name, "passages": passages}

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
                }
                for citation in result.citations
            ],
        }

    return app
