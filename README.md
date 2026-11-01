# Enterprise Document Assistant

Add PDFs, Markdown, and plain-text manuals, then ask a Question. The answer cites the Passages it used. Open http://127.0.0.1:8000 after the server starts.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn document_assistant.asgi:app --app-dir src --port 8000
```

The server reads `.env` on startup. Without `OPENAI_API_KEY` and Pinecone settings, the service uses an in-memory Corpus and returns the most relevant Passage as the Grounded answer. Restart the server after changing `.env`.

## Try

```bash
curl -F "file=@samples/vacation-policy.md" http://127.0.0.1:8000/documents
curl -H "content-type: application/json" \
  -d '{"question":"How many vacation days do employees receive?"}' \
  http://127.0.0.1:8000/questions
```

## Web page

- Drop one or more files anywhere on the page (or click **Add documents**). Adding a file with the same name replaces the earlier version.
- The Documents panel lists everything in the Corpus with Passage and page counts; hover a row to remove it.
- Ask with <kbd>Enter</kbd> (<kbd>Shift</kbd>+<kbd>Enter</kbd> for a new line). Each answer shows numbered Citations with the page, a similarity score, and the Question's terms highlighted. With an OpenAI key, the answer marks claims like `[1]`; click a marker to jump to its Citation.
- The header shows which model and store are active.

## HTTP API

| Route | Purpose |
| --- | --- |
| `GET /health` | `{ "status": "ok", "store": "memory" \| "pinecone", "answerer": "passage" \| "openai" }` |
| `GET /documents` | Documents added since the server started: `[{ "document", "passages", "pages" }]` |
| `POST /documents` | Multipart `file` (max 25 MB). Returns `{ "document", "passages", "replaced" }` |
| `DELETE /documents/{name}` | Removes a Document's Passages from the Corpus |
| `POST /questions` | `{ "question" }` returns `{ "answer", "citations": [{ "document", "page", "excerpt", "score" }] }` |

With Pinecone, `GET /documents` lists only Documents added since the server started; Passages from earlier runs remain searchable.


## Evals

`evals/` holds an eval harness: 37 labeled Questions over a fixed Corpus, scored for retrieval
(hit@k, recall, MRR), answer accuracy, refusals, citation validity, faithfulness (LLM judge),
latency and cost. See `evals/README.md`.

```bash
python evals/run_eval.py --offline   # or without --offline to use OpenAI
```
