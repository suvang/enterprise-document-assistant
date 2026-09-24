# 01: Ask a Question against an indexed Corpus

**Status:** ready-for-agent

## Parent

`.scratch/document-assistant/spec.md`

## What to build

A caller who already has Passages in the Corpus can ask a Question and receive a Grounded answer whose Citations name those Passages.

## Acceptance criteria

- [ ] Adding a short text Document puts its text in the Corpus as a Passage
- [ ] Asking a Question that matches that Passage returns the answerer's text
- [ ] The Citation names the Document, the page when one was stored, and the Passage text
- [ ] At most four Citations are returned when more Passages match
- [ ] The answerer receives only those retrieved Passages

## Blocked by

None (can start immediately).
