# 05: Select the Pinecone adapter from the environment

**Status:** ready-for-agent

## Parent

`.scratch/document-assistant/spec.md`

## What to build

The assistant service keeps the same add-and-ask seam. The vector-store adapter is Pinecone when both Pinecone environment variables are set, and the in-memory adapter otherwise.

## Acceptance criteria

- [ ] Missing Pinecone settings select the in-memory adapter
- [ ] `PINECONE_API_KEY` and `PINECONE_INDEX` together select the Pinecone adapter
- [ ] Only one of those settings still selects the in-memory adapter
- [ ] Building the Pinecone adapter does not require a live Pinecone call in the test

## Blocked by

- 02 Add a text or PDF Document, then ask
