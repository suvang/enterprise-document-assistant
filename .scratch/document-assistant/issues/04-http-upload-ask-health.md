# 04: Add, ask, and health over HTTP

**Status:** ready-for-agent

## Parent

`.scratch/document-assistant/spec.md`

## What to build

A running service accepts a Document upload, accepts a Question, and reports that it is up. The Question response is the Grounded answer and its Citations.

## Acceptance criteria

- [ ] `GET /health` returns status ok
- [ ] `POST /documents` accepts a text manual and reports how many Passages were added
- [ ] `POST /questions` returns the Grounded answer and Citations for that manual
- [ ] The HTTP shapes match the spec: question in, answer plus citations out

## Blocked by

- 02 Add a text or PDF Document, then ask
- 03 Refuse when no Passage is relevant
