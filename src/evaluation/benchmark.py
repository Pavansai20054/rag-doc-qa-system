from src.evaluation.metrics import recall_at_k, mrr, groundedness_score


SAMPLE_QUERIES = [
    {
        "question": "What is the VPN access policy?",
        "relevant_sources": {"VPN_Guide.docx"},
    },
    {
        "question": "How do we handle incident response escalation?",
        "relevant_sources": {"SecurityPolicy.pdf"},
    },
]


def run_benchmark(retriever, qa_fn) -> None:
    recall_scores = []
    mrr_scores = []
    grounded_scores = []
    for item in SAMPLE_QUERIES:
        retrieved = retriever.retrieve(item["question"], top_k=10)
        sources = [r["payload"]["metadata"].get("filename", "") for r in retrieved]
        recall_scores.append(recall_at_k(item["relevant_sources"], sources, 10))
        mrr_scores.append(mrr(item["relevant_sources"], sources))

        answer = qa_fn(item["question"], retrieved)
        grounded_scores.append(
            groundedness_score([r["payload"]["text"] for r in retrieved], answer)
        )

    print("Recall@10:", sum(recall_scores) / len(recall_scores))
    print("MRR:", sum(mrr_scores) / len(mrr_scores))
    print("Groundedness:", sum(grounded_scores) / len(grounded_scores))


if __name__ == "__main__":
    print("Wire this script with your retriever and QA chain to run evaluation.")
