from src.utils.metadata import DocumentChunk


def build_prompt(question: str, context_chunks: list[DocumentChunk]) -> str:
    context_lines = []
    for chunk in context_chunks:
        meta = chunk["metadata"]
        source = meta.get("filename", "unknown")
        page = meta.get("page_number")
        section = meta.get("section_heading")
        location = []
        if page:
            location.append(f"Page {page}")
        if section:
            location.append(f"Section {section}")
        location_text = " - ".join(location) if location else ""
        citation = f"[{source}{' - ' + location_text if location_text else ''}]"
        context_lines.append(f"{citation} {chunk['text']}")
    context = "\n\n".join(context_lines)
    return (
        "You are an enterprise RAG assistant. Use only the context below. "
        "If the answer is missing, say you do not have enough information. "
        "Always add citations in the form [Source - Location].\n\n"
        "Answer format:\n"
        "- Provide 3-6 bullet points for the direct answer.\n"
        "- Follow with 1-2 short paragraphs that explain the reasoning.\n"
        "- Include 2-4 brief quoted excerpts from the context with citations.\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}\n\n"
        "Answer:"
    )
