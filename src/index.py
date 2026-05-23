import argparse

from src.chunking.chunker import recursive_chunk, semantic_chunk
from src.embeddings.embedding_model import EmbeddingModel
from src.ingestion.loaders import load_all
from src.utils.config import load_settings
from src.utils.dedup import stable_hash
from src.vectordb.qdrant_store import QdrantStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Index enterprise documents into Qdrant")
    parser.add_argument("--source", required=True, help="Root folder with docs")
    parser.add_argument("--semantic", action="store_true", help="Use semantic chunking")
    args = parser.parse_args()

    settings = load_settings()
    embedding_model = EmbeddingModel(settings.embedding_model)
    vector_store = QdrantStore(
        settings.qdrant_url,
        settings.qdrant_collection,
        embedding_model.model.get_sentence_embedding_dimension(),
    )

    docs = list(load_all(args.source))
    if args.semantic:
        chunks = semantic_chunk(
            docs, settings.chunk_size, settings.chunk_overlap, settings.embedding_model
        )
    else:
        chunks = recursive_chunk(docs, settings.chunk_size, settings.chunk_overlap)

    texts = [c["text"] for c in chunks if c.get("text")]
    payloads = [
        {
            "text": c["text"],
            "hash": stable_hash(c["text"]),
            "metadata": c["metadata"],
        }
        for c in chunks
    ]

    if not texts:
        print("No text extracted from documents. Check the source path and file types.")
        return

    embeddings = embedding_model.embed_documents(texts)
    vector_store.upsert(embeddings, payloads, batch_size=64)
    print(f"Indexed {len(texts)} chunks")


if __name__ == "__main__":
    main()
