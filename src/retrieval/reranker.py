"""Reranker. Default: lightweight lexical-overlap rerank. Optional: cross-encoder if installed."""
from src.vectorstore.bm25_index import tokenize


class OverlapReranker:
    def rerank(self, query: str, hits: list[dict], k: int) -> list[dict]:
        q = set(tokenize(query))
        for h in hits:
            t = set(tokenize(h["text"]))
            h["rerank_score"] = h["score"] + 0.5 * (len(q & t) / (len(q) or 1))
        return sorted(hits, key=lambda h: -h["rerank_score"])[:k]


class CrossEncoderReranker:
    def __init__(self, name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(name)

    def rerank(self, query: str, hits: list[dict], k: int) -> list[dict]:
        scores = self.model.predict([(query, h["text"]) for h in hits])
        for h, s in zip(hits, scores):
            h["rerank_score"] = float(s)
        return sorted(hits, key=lambda h: -h["rerank_score"])[:k]
