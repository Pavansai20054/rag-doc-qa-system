from pydantic import BaseModel


class IngestRequest(BaseModel):
    source_path: str
    semantic_chunking: bool = False


class QueryRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    metadata_filters: dict[str, str] | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[str]
    conversation_id: str
    retrieved_chunks: list[dict]
