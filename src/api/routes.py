import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.schemas import IngestRequest, QueryRequest, QueryResponse
from src.api.state import CONVERSATIONS
from src.chunking.chunker import recursive_chunk, semantic_chunk
from src.embeddings.embedding_model import EmbeddingModel
from src.ingestion.loaders import load_all
from src.llm.nvidia_client import NvidiaLlamaClient
from src.llm.qa_chain import build_prompt
from src.reranking.cross_encoder import CrossEncoderReranker
from src.retrieval.hybrid_retriever import HybridRetriever
from src.utils.config import load_settings
from src.utils.cache import LRUCache
from src.utils.logging import get_logger
from src.utils.dedup import stable_hash
from src.utils.metadata import DocumentChunk
from src.vectordb.qdrant_store import QdrantStore

router = APIRouter()

settings = load_settings()
logger = get_logger("rag.api")
embedding_model = EmbeddingModel(settings.embedding_model)
reranker = CrossEncoderReranker(settings.reranker_model)
vector_store = QdrantStore(
    settings.qdrant_url, settings.qdrant_collection, embedding_model.model.get_sentence_embedding_dimension()
)
llm_client = NvidiaLlamaClient(settings)

BM25_TEXTS: list[str] = []
BM25_PAYLOADS: list[dict] = []
DEDUP_HASHES: set[str] = set()
CACHE = LRUCache(capacity=256)


@router.post("/ingest")
def ingest(request: IngestRequest) -> dict:
    logger.info("ingest_start source=%s semantic=%s", request.source_path, request.semantic_chunking)
    docs = list(load_all(request.source_path))
    logger.info("ingest_loaded docs=%s", len(docs))
    if request.semantic_chunking:
        chunks = semantic_chunk(
            docs, settings.chunk_size, settings.chunk_overlap, settings.embedding_model
        )
    else:
        chunks = recursive_chunk(docs, settings.chunk_size, settings.chunk_overlap)
    logger.info("ingest_chunked chunks=%s", len(chunks))

    payloads = []
    texts = []
    for chunk in chunks:
        chunk_hash = stable_hash(chunk["text"])
        if chunk_hash in DEDUP_HASHES:
            continue
        payloads.append({
            "text": chunk["text"],
            "hash": chunk_hash,
            "metadata": chunk["metadata"],
        })
        texts.append(chunk["text"])
        DEDUP_HASHES.add(chunk_hash)

    if texts:
        embeddings = embedding_model.embed_documents(texts)
        vector_store.upsert(embeddings, payloads)

        BM25_TEXTS.extend(texts)
        BM25_PAYLOADS.extend(payloads)
        logger.info("ingest_upserted points=%s", len(texts))
    else:
        logger.warning("ingest_no_texts")

    return {"chunks_indexed": len(chunks)}


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    conversation_id = request.conversation_id or str(uuid.uuid4())
    history = CONVERSATIONS.get(conversation_id)
    logger.info(
        "query_start conversation_id=%s question=%s",
        conversation_id,
        request.question,
    )

    cache_key = f"{conversation_id}:{request.question}:{request.metadata_filters}"
    cached = CACHE.get(cache_key)
    if cached:
        logger.info("query_cache_hit conversation_id=%s", conversation_id)
        return cached

    if not BM25_TEXTS:
        raise HTTPException(status_code=400, detail="No documents indexed yet.")

    retriever = HybridRetriever(
        embedding_model=embedding_model,
        vector_store=vector_store,
        bm25_texts=BM25_TEXTS,
        bm25_payloads=BM25_PAYLOADS,
    )
    retrieved = retriever.retrieve(
        request.question, top_k=15, metadata_filters=request.metadata_filters
    )
    logger.info("query_retrieved count=%s", len(retrieved))
    reranked = reranker.rerank(request.question, retrieved, top_k=5)
    logger.info("query_reranked count=%s", len(reranked))

    context_chunks: list[DocumentChunk] = []
    citations: list[str] = []
    for item in reranked:
        payload = item["payload"]
        context_chunks.append(
            {"text": payload["text"], "metadata": payload["metadata"]}
        )
        meta = payload["metadata"]
        source = meta.get("filename", "unknown")
        page = meta.get("page_number")
        section = meta.get("section_heading")
        if page:
            citations.append(f"[{source} - Page {page}]")
        elif section:
            citations.append(f"[{source} - Section {section}]")
        else:
            citations.append(f"[{source}]")

    prompt = build_prompt(request.question, context_chunks)
    messages = history + [{"role": "user", "content": prompt}]
    response = llm_client.chat(messages)
    answer = response["choices"][0]["message"]["content"]
    logger.info("query_llm_done conversation_id=%s", conversation_id)

    CONVERSATIONS.append(conversation_id, {"role": "user", "content": request.question})
    CONVERSATIONS.append(conversation_id, {"role": "assistant", "content": answer})

    response_obj = QueryResponse(
        answer=answer,
        citations=citations,
        conversation_id=conversation_id,
        retrieved_chunks=[
            {"text": c["text"], "metadata": c["metadata"]} for c in context_chunks
        ],
    )
    CACHE.set(cache_key, response_obj)
    return response_obj


@router.post("/query/stream")
def query_stream(request: QueryRequest):
    conversation_id = request.conversation_id or str(uuid.uuid4())
    history = CONVERSATIONS.get(conversation_id)

    if not BM25_TEXTS:
        raise HTTPException(status_code=400, detail="No documents indexed yet.")

    retriever = HybridRetriever(
        embedding_model=embedding_model,
        vector_store=vector_store,
        bm25_texts=BM25_TEXTS,
        bm25_payloads=BM25_PAYLOADS,
    )
    retrieved = retriever.retrieve(
        request.question, top_k=15, metadata_filters=request.metadata_filters
    )
    reranked = reranker.rerank(request.question, retrieved, top_k=5)

    context_chunks: list[DocumentChunk] = []
    for item in reranked:
        payload = item["payload"]
        context_chunks.append(
            {"text": payload["text"], "metadata": payload["metadata"]}
        )

    prompt = build_prompt(request.question, context_chunks)
    messages = history + [{"role": "user", "content": prompt}]

    def stream_generator():
        accumulated = []
        for token in llm_client.stream_chat(messages):
            accumulated.append(token)
            yield token
        CONVERSATIONS.append(conversation_id, {"role": "user", "content": request.question})
        CONVERSATIONS.append(
            conversation_id, {"role": "assistant", "content": "".join(accumulated)}
        )

    return StreamingResponse(stream_generator(), media_type="text/plain")
