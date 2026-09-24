# 03: Refuse when no Passage is relevant

**Status:** ready-for-agent

## Parent

`.scratch/document-assistant/spec.md`

## What to build

Asking a Question when the Corpus has no relevant Passage returns the refusal sentence and no Citations, and does not call the answerer.

## Acceptance criteria

- [ ] A Question against an empty Corpus returns `The documents do not contain an answer to that question.` and no Citations
- [ ] A Question that does not match the stored Passages returns that same sentence and no Citations
- [ ] The answerer is not called in either case
- [ ] A blank Question is rejected

## Blocked by

- 01 Ask a Question against an indexed Corpus
