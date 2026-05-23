from typing import Any, TypedDict


class DocumentChunk(TypedDict):
    text: str
    metadata: dict[str, Any]
