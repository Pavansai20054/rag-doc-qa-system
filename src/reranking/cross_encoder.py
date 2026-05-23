from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    def __init__(self, model_name: str):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        pairs = [(query, c["payload"]["text"]) for c in candidates]
        scores = self.model.predict(pairs)
        scored = [
            {"score": float(score), "payload": cand["payload"]}
            for score, cand in zip(scores, candidates)
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
