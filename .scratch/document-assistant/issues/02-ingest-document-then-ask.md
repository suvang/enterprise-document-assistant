# 02: Add a text or PDF Document, then ask

**Status:** ready-for-agent

## Parent

`.scratch/document-assistant/spec.md`

## What to build

A caller can add a Markdown, plain-text, or PDF Document. Long text becomes multiple Passages. A later Question cites the Passage that supports it, including the PDF page.

## Acceptance criteria

- [ ] A Markdown or plain-text Document longer than one Passage is split, and a Question cites the Passage that contains the fact
- [ ] A PDF Document is added, and the Citation includes the page the loader reports
- [ ] An empty Document adds zero Passages
- [ ] A Document whose type is not PDF, Markdown, or plain text is rejected and does not enter the Corpus

## Blocked by

- 01 Ask a Question against an indexed Corpus
