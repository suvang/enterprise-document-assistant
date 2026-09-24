# Document Assistant

Teams search PDFs, reports, and internal manuals that are spread across many files, and get answers that stay tied to those files.

## Language

**Document**:
A PDF, Markdown, or plain-text manual a team adds so it can be searched.
_Avoid_: File, source, article, upload

**Passage**:
A contiguous section of a Document small enough to retrieve on its own.
_Avoid_: Chunk, snippet, embedding

**Corpus**:
The set of Passages currently available to answer Questions.
_Avoid_: Index, knowledge base, collection

**Question**:
A natural-language request for information that should be answered from the Corpus.
_Avoid_: Query, prompt, search

**Grounded answer**:
An answer whose claims come only from retrieved Passages, or an explicit statement that the Documents do not contain the answer.
_Avoid_: Response, completion, hallucination

**Citation**:
A pointer from a Grounded answer back to the Document and Passage that support it.
_Avoid_: Source, reference, footnote
