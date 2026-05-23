from typing import Iterable

from langchain_text_splitters import RecursiveCharacterTextSplitter, TokenTextSplitter
from sentence_transformers import SentenceTransformer

from src.utils.metadata import DocumentChunk
from src.utils.text import split_sentences


def recursive_chunk(
    docs: Iterable[DocumentChunk], chunk_size: int, chunk_overlap: int
) -> list[DocumentChunk]:
    try:
        splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    except Exception:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
    chunks: list[DocumentChunk] = []
    for doc in docs:
        for idx, piece in enumerate(splitter.split_text(doc["text"])):
            chunks.append(
                {
                    "text": piece,
                    "metadata": {
                        **doc["metadata"],
                        "chunk_id": idx,
                    },
                }
            )
    return chunks


def semantic_chunk(
    docs: Iterable[DocumentChunk],
    chunk_size: int,
    chunk_overlap: int,
    embedding_model: str,
    similarity_threshold: float = 0.55,
) -> list[DocumentChunk]:
    model = SentenceTransformer(embedding_model)
    chunks: list[DocumentChunk] = []
    for doc in docs:
        sentences = split_sentences(doc["text"])
        if not sentences:
            continue
        embeddings = model.encode(sentences, normalize_embeddings=True)
        current: list[str] = []
        current_tokens = 0
        chunk_id = 0
        for idx, sentence in enumerate(sentences):
            token_estimate = len(sentence.split())
            if current and current_tokens + token_estimate > chunk_size:
                chunks.append(
                    {
                        "text": " ".join(current),
                        "metadata": {**doc["metadata"], "chunk_id": chunk_id},
                    }
                )
                chunk_id += 1
                overlap_tokens = 0
                overlap: list[str] = []
                for s in reversed(current):
                    overlap_tokens += len(s.split())
                    overlap.append(s)
                    if overlap_tokens >= chunk_overlap:
                        break
                current = list(reversed(overlap))
                current_tokens = overlap_tokens
            if current:
                similarity = float(embeddings[idx - 1] @ embeddings[idx])
                if similarity < similarity_threshold:
                    chunks.append(
                        {
                            "text": " ".join(current),
                            "metadata": {**doc["metadata"], "chunk_id": chunk_id},
                        }
                    )
                    chunk_id += 1
                    current = []
                    current_tokens = 0
            current.append(sentence)
            current_tokens += token_estimate
        if current:
            chunks.append(
                {
                    "text": " ".join(current),
                    "metadata": {**doc["metadata"], "chunk_id": chunk_id},
                }
            )
    return chunks
