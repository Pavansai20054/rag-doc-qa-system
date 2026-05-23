# Pipeline Design Q&A

## Design the pipeline

I would build a clear, staged pipeline: ingest documents (PDF/DOCX/HTML/TXT), normalize and clean the text, chunk into coherent segments with overlap, embed each chunk, and store both vectors and metadata in Qdrant. At query time, I run hybrid retrieval (dense + BM25), rerank with a cross-encoder, and then synthesize a grounded response using the NVIDIA Llama API. Every chunk keeps metadata so the final answer can cite sources precisely.

## What you'd use for chunking and why

I'd use `recursive character splitting` with a chunk size of 512 tokens and 50-100 token overlap. The reason is simple — fixed-size splitting is predictable and works well across mixed formats (PDF, Word, Confluence). Semantic chunking sounds better on paper but it's slower, harder to debug, and inconsistent across document types. The overlap ensures context doesn't get cut off at chunk boundaries, which matters when a sentence spans two chunks.

For PDFs specifically, I'd extract text page by page first, then chunk — not dump the whole PDF into one string and split blindly, because page breaks often carry structural meaning.

## Embedding model choice

`sentence-transformers/all-MiniLM-L6-v2` for cost-sensitive or self-hosted setups, or `text-embedding-3-small` from OpenAI if API budget allows. Both handle semantic similarity well. I'd avoid using a general-purpose model like ada-002 for domain-specific internal docs — fine-tuning or at least evaluating retrieval quality on a sample set matters here.

## Vector store choice

Qdrant. It supports hybrid search natively (dense + sparse/BM25 in one query), has good filtering on metadata, and is easy to self-host with Docker. For 10,000 documents that's a manageable scale — no need for something like Weaviate or Pinecone unless you're scaling to millions.

## Retrieval strategy

Hybrid retrieval — dense vector search combined with BM25 keyword search, scores merged via Reciprocal Rank Fusion. Dense handles semantic queries, BM25 handles exact terminology (product names, policy codes, IDs). Using only dense search fails on queries like "what is policy HR-204" where keyword matching is more reliable.

After retrieval, run a cross-encoder reranker on top 15 results and pass the top 5 to the LLM. The reranker is slower but significantly improves precision — it reads query and chunk together rather than comparing embeddings independently.

## How you'd handle documents that answer the question only partially

If no single chunk fully answers the question, the system should still return what it found with clear citations, and explicitly tell the user which part of the question it couldn't fully answer. In the prompt I'd instruct the LLM: "If the context only partially answers the question, answer what you can and clearly state what information is missing." This is better than either hallucinating a complete answer or refusing to answer at all.

## Biggest failure mode

Retrieval returning irrelevant chunks — the LLM then either hallucinates an answer or confidently answers from the wrong context. This is the silent killer because it looks like the system is working but it's producing wrong answers with no error thrown.

## Mitigation

The main fix is a relevance score threshold — if the top retrieved chunk scores below a set confidence level after reranking, the system returns "I don't have enough information to answer this reliably" instead of passing low-quality context to the LLM. Beyond that, I'd log every retrieval decision with scores so I can audit and tune the threshold over time. Tracking Recall@K and MRR on a test query set helps catch drift early before it affects users.
