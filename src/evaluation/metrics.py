from typing import Iterable


def recall_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    hits = len(set(retrieved[:k]) & relevant)
    return hits / float(len(relevant))


def mrr(relevant: set[str], retrieved: list[str]) -> float:
    for idx, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / idx
    return 0.0


def groundedness_score(retrieved: Iterable[str], answer: str) -> float:
    answer_tokens = set(answer.lower().split())
    retrieved_tokens = set(" ".join(retrieved).lower().split())
    if not answer_tokens:
        return 0.0
    return len(answer_tokens & retrieved_tokens) / float(len(answer_tokens))
