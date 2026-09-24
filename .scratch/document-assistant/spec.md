# Grounded answers from enterprise Documents

Status: ready-for-agent

## Problem Statement

Teams keep policies, reports, and manuals in many PDFs and text files. People cannot reliably find the right section, and an ungrounded answer can state something the Documents never said.

## Solution

A person adds Documents, asks a Question, and receives a Grounded answer with Citations. The answer uses only the retrieved Passages. If none are relevant, the answer says the Documents do not contain it.

## User Stories

1. As a team member, I want to add a PDF Document, so that its Passages become part of the Corpus.
2. As a team member, I want to add a Markdown Document, so that internal manuals written in Markdown can be searched.
3. As a team member, I want to add a plain-text Document, so that exported manuals can be searched.
4. As a team member, I want to know how many Passages a Document produced, so that I can tell the add succeeded.
5. As a team member, I want to ask a Question in natural language, so that I do not have to guess keywords.
6. As a team member, I want a Grounded answer written from the retrieved Passages, so that the reply stays aligned with the Documents.
7. As a team member, I want each Citation to name the Document, so that I can open the right file.
8. As a team member, I want a Citation for a PDF to include the page, so that I can jump to the right place.
9. As a team member, I want each Citation to include the Passage text, so that I can check the claim without re-reading the whole Document.
10. As a team member, I want at most four Passages used for a Question, so that the answer stays focused on the closest sections.
11. As a team member, I want an explicit statement when the Corpus has nothing relevant, so that I am not given an invented answer.
12. As a team member, I want that refusal to include no Citations, so that I do not follow empty pointers.
13. As a team member, I want a blank Question rejected, so that I know I still need to ask something.
14. As a team member, I want an unsupported Document type rejected, so that I know it was not added to the Corpus.
15. As a team member, I want to ask again after adding another Document, so that later Questions can use the growing Corpus.
16. As a team member, I want Citations to name the Document that actually contains the Passage, so that two manuals are not mixed up.
17. As an operator, I want a health check, so that I can tell the service is up.
18. As an operator, I want to add a Document over HTTP, so that another system can feed the Corpus.
19. As an operator, I want to ask a Question over HTTP and receive the Grounded answer and Citations, so that a client can show them.
20. As an operator, I want Pinecone used when its credentials are set, so that the Corpus survives restarts in a hosted index.
21. As an operator, I want the in-memory Corpus when Pinecone credentials are absent, so that local runs and tests need no cloud account.
22. As an operator, I want the same ask-and-cite behavior on either store, so that the choice of store does not change the Grounded answer contract.
23. As a team member, I want the language model to see only the retrieved Passages, so that it cannot smuggle in outside facts.
24. As an operator, I want a local stand-in answer when no OpenAI key is set, so that the service can be tried without a model account. The stand-in text is the most relevant Passage.
25. As a team member, I want an empty Document to add nothing, so that a blank file does not create a fake Passage.

## Implementation Decisions

- The only test seam is the assistant service: add a Document, ask a Question, receive a Grounded answer. HTTP is a thin adapter over that service.
- A Document is split into Passages with a recursive character splitter at 1000 characters and 200 characters of overlap. Each Passage keeps the Document name, the page when the loader has one, and a chunk index starting at 0.
- PDF pages come from the loader. Markdown and plain text have no page.
- Embeddings are OpenAI `text-embedding-3-small` when `OPENAI_API_KEY` is set. Questions and Passages use the same embedder.
- The chat model is OpenAI `gpt-4o-mini` when `OPENAI_API_KEY` is set. Its prompt contains the Question and the retrieved Passage texts only, and instructs it to use nothing else.
- When `OPENAI_API_KEY` is absent, the Grounded answer text is the text of the most relevant Passage. Citations are unchanged.
- A vector-store port has two adapters. Pinecone is selected when both `PINECONE_API_KEY` and `PINECONE_INDEX` are set. Otherwise the in-memory adapter is used.
- Retrieval keeps the top 4 Passages whose cosine similarity to the Question is at least 0.25. Below that, the Passage is not relevant.
- When no Passage is relevant, the Grounded answer text is exactly `The documents do not contain an answer to that question.` and the Citation list is empty. The language model is not called.
- A blank Question is rejected. A Document whose name does not end in `.pdf`, `.md`, `.markdown`, or `.txt` is rejected.
- Supported HTTP routes: `POST /documents` (multipart file), `POST /questions` with `{ "question": "..." }` returning `{ "answer", "citations" }`, and `GET /health` returning `{ "status": "ok" }`. Each Citation has `document`, `page`, and `excerpt`.

## Testing Decisions

- Test external behavior through the assistant service. Do not assert on LangChain internals or Pinecone calls.
- Good tests state what a caller can do: add a Document, ask a Question, and observe the Grounded answer and Citations. Expected text is a known literal, not a value recomputed the way the implementation does.
- The language model, the embedding API, and Pinecone are system boundaries. Tests inject a scripted embedder, a scripted answerer, and the in-memory store. They never call OpenAI or Pinecone.
- The store-selection behavior is tested by checking which adapter is chosen from the environment, with Pinecone construction injected so no network call is made.
- HTTP is checked by calling the running service, not by a second test seam.

## Out of Scope

Authentication, multi-tenant collections, a web page, a command-line interface, LlamaIndex, evaluation dashboards, and deployment.

## Further Notes

The approved plan is the shared understanding for this spec. The test seam is the assistant service only.
