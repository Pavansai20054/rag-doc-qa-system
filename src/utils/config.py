import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value or ""


@dataclass(frozen=True)
class Settings:
    nvidia_api_key: str
    nvidia_model: str
    qdrant_url: str
    qdrant_collection: str
    embedding_model: str
    reranker_model: str
    chunk_size: int
    chunk_overlap: int


def load_settings() -> Settings:
    load_dotenv(override=False)
    return Settings(
        nvidia_api_key=_get_env("NVIDIA_API_KEY", required=True),
        nvidia_model=_get_env(
            "NVIDIA_MODEL", "meta/llama-4-maverick-17b-128e-instruct"
        ),
        qdrant_url=_get_env("QDRANT_URL", "http://localhost:6333"),
        qdrant_collection=_get_env("QDRANT_COLLECTION", "enterprise_knowledge"),
        embedding_model=_get_env(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
        reranker_model=_get_env(
            "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        ),
        chunk_size=int(_get_env("CHUNK_SIZE", "650")),
        chunk_overlap=int(_get_env("CHUNK_OVERLAP", "120")),
    )
