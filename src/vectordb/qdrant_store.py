import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)


class QdrantStore:
    def __init__(self, url: str, collection: str, vector_size: int):
        self.client = QdrantClient(url=url)
        self.collection = collection
        self.vector_size = vector_size
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

    def upsert(
        self,
        embeddings: list[list[float]],
        payloads: list[dict[str, Any]],
        batch_size: int = 64,
    ) -> None:
        for start in range(0, len(embeddings), batch_size):
            batch_embeddings = embeddings[start : start + batch_size]
            batch_payloads = payloads[start : start + batch_size]
            points = [
                PointStruct(id=str(uuid.uuid4()), vector=vec, payload=payload)
                for vec, payload in zip(batch_embeddings, batch_payloads)
            ]
            self.client.upsert(collection_name=self.collection, points=points)

    def search(
        self,
        vector: list[float],
        top_k: int = 10,
        search_filter: Filter | None = None,
    ) -> list[dict[str, Any]]:
        results = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter=search_filter,
            limit=top_k,
        )
        return [
            {
                "score": res.score,
                "payload": res.payload,
            }
            for res in results
        ]

    @staticmethod
    def build_filter(metadata_filters: dict[str, str] | None) -> Filter | None:
        if not metadata_filters:
            return None
        conditions = []
        for key, value in metadata_filters.items():
            conditions.append(
                FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value))
            )
        return Filter(must=conditions)
