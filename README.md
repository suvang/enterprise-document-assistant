"""Enterprise Document Assistant

Add PDFs, Markdown, and plain-text manuals, then ask a Question. The answer cites the Passages it used.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn document_assistant.asgi:app --app-dir src --port 8000
```

Without `OPENAI_API_KEY` and Pinecone settings, the service uses an in-memory Corpus and returns the most relevant Passage as the Grounded answer.

## Try

```bash
curl -F "file=@samples/vacation-policy.md" http://127.0.0.1:8000/documents
curl -H "content-type: application/json" \
  -d '{"question":"How many vacation days do employees receive?"}' \
  http://127.0.0.1:8000/questions
```
