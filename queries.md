# Pipeline Design Q&A

## Design the pipeline

I would build a clear, staged pipeline: ingest documents (PDF/DOCX/HTML/TXT), normalize and clean the text, chunk into coherent segments with overlap, embed each chunk, and store both vectors and metadata in Qdrant. At query time, I run hybrid retrieval (dense + BM25), rerank with a cross-encoder, and then synthesize a grounded response using the NVIDIA Llama API. Every chunk keeps metadata so the final answer can cite sources precisely.

## What you'd use for chunking and why

I use `RecursiveCharacterTextSplitter` with 500-700 token chunks and 100-150 token overlap. That size is large enough to preserve context, but small enough to remain focused on a single idea. Overlap is important because enterprise policies often span multiple sentences; without overlap you lose meaning across boundaries and citations become brittle.

## Embedding model choice

I start with `sentence-transformers/all-MiniLM-L6-v2` because it is fast, reliable, and cheap to run at scale. If recall and semantic coverage become a concern, I move to `BAAI/bge-large-en-v1.5` for stronger semantic fidelity. The tradeoff is higher memory use and slower embedding latency, so I only upgrade once the baseline shows limits.

## Vector store choice

Qdrant is a good fit because it is fast, production-ready, supports metadata filtering, and has a clean API for both upserts and hybrid retrieval workflows. It scales well and works locally during development without changing code.

## Retrieval strategy

I use hybrid retrieval: dense vector search for semantic relevance and BM25 for exact keywords, identifiers, and acronyms. The merged results are reranked with a cross-encoder to tighten precision. This combination consistently beats vector-only retrieval on policy and compliance content where exact terms matter.

## How you'd handle documents that answer the question only partially

I retrieve more than I need (top 15), rerank, and then assemble the best 5 for the LLM. That gives the model enough evidence to merge partial answers from multiple documents while still keeping a tight context window. I also keep citations tied to each chunk so the final response is traceable.

## Biggest failure mode

Retrieval failure is the biggest risk. If the system misses the right chunk, the model can still produce a confident answer that is wrong or incomplete.

## Mitigation

I mitigate this with hybrid retrieval, reranking, query expansion, metadata filters, and careful chunking. I also track retrieval metrics (Recall@K, MRR) and log top results to audit whether the system is actually surfacing the correct evidence. If recall drops, I retune chunk sizes, embeddings, or reranker thresholds.
