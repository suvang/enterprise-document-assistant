# LangChain pipeline behind a vector-store port

The assistant loads, splits, embeds, and answers with LangChain. Pinecone stores Passages when its credentials are set. An in-memory store implements the same port so tests and local runs do not need Pinecone. LlamaIndex was rejected because it would duplicate the LangChain pipeline.

## Considered options

- LlamaIndex plus Pinecone
- LangChain plus Pinecone, with an in-memory adapter of the same port
- Both frameworks, split between ingestion and answering
