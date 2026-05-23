from typing import Any

from rank_bm25 import BM25Okapi

from src.embeddings.embedding_model import EmbeddingModel
from src.vectordb.qdrant_store import QdrantStore


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _expand_query(query: str) -> str:
    synonym_map = {
        "vpn": ["remote access", "tunnel", "secure access"],
        "incident": ["outage", "security event", "escalation"],
        "policy": ["procedure", "guideline"],
        "kubernetes": ["k8s", "cluster"],
    }
    additions = []
    for token in _tokenize(query):
        additions.extend(synonym_map.get(token, []))
    if additions:
        return f"{query} {' '.join(additions)}"
    return query


def _passes_filters(payload: dict[str, Any], metadata_filters: dict[str, str] | None) -> bool:
    if not metadata_filters:
        return True
    metadata = payload.get("metadata", {})
    for key, value in metadata_filters.items():
        if str(metadata.get(key)) != str(value):
            return False
    return True


def _rrf_fusion(dense: list[dict[str, Any]], bm25: list[dict[str, Any]]) -> list[dict]:
    scores: dict[str, float] = {}
    payloads: dict[str, dict[str, Any]] = {}
    for rank, item in enumerate(dense, start=1):
        key = item["payload"]["hash"]
        scores[key] = scores.get(key, 0.0) + 1.0 / (rank + 60)
        payloads[key] = item["payload"]
    for rank, item in enumerate(bm25, start=1):
        key = item["payload"]["hash"]
        scores[key] = scores.get(key, 0.0) + 1.0 / (rank + 60)
        payloads[key] = item["payload"]
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [
        {
            "score": score,
            "payload": payloads[key],
        }
        for key, score in ranked
    ]


class HybridRetriever:
    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: QdrantStore,
        bm25_texts: list[str],
        bm25_payloads: list[dict[str, Any]],
    ):
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.bm25 = BM25Okapi([_tokenize(t) for t in bm25_texts])
        self.bm25_payloads = bm25_payloads

    def retrieve(
        self,
        query: str,
        top_k: int = 15,
        metadata_filters: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        expanded_query = _expand_query(query)
        query_vec = self.embedding_model.embed_query(expanded_query)
        search_filter = self.vector_store.build_filter(metadata_filters)
        dense = self.vector_store.search(
            query_vec, top_k=top_k, search_filter=search_filter
        )
        bm25_scores = self.bm25.get_scores(_tokenize(expanded_query))
        bm25_ranked = sorted(
            enumerate(bm25_scores), key=lambda x: x[1], reverse=True
        )
        bm25_results = []
        for idx, score in bm25_ranked:
            payload = self.bm25_payloads[idx]
            if _passes_filters(payload, metadata_filters):
                bm25_results.append({"score": score, "payload": payload})
            if len(bm25_results) >= top_k:
                break
        fused = _rrf_fusion(dense, bm25_results)
        return fused[:top_k]
