"""Hybrid retrieval = dense (vectors) + BM25, fused with Reciprocal Rank Fusion, then reranked."""
from src.retrieval.reranker import OverlapReranker
from src.vectorstore.bm25_index import BM25Index


class HybridRetriever:
    def __init__(self, indexes: dict, embedder, reranker=None, mode: str = "hybrid_rerank"):
        """indexes: {"approved": VectorIndex, "rejected": VectorIndex}.
        mode: dense | bm25 | hybrid | hybrid_rerank (used for the ablation table)."""
        self.indexes, self.embedder = indexes, embedder
        self.reranker = reranker or OverlapReranker()
        self.mode = mode
        self._bm25 = {n: BM25Index([r["text"] for r in ix.records]) for n, ix in indexes.items()}

    @staticmethod
    def _is(rec: dict, corpus: str | None) -> bool:
        c = rec.get("corpus") or "grant"          # records without a corpus are grant records
        return corpus is None or c == corpus

    def _search_one(self, lib: str, query: str, qvec, pool: int, corpus: str | None = None) -> list[dict]:
        ix = self.indexes[lib]
        wide = len(ix.records) if corpus else pool   # filter by corpus BEFORE cutting to the pool
        dense = ix.search(qvec, wide) if self.mode != "bm25" else []
        lex = self._bm25[lib].search(query, wide) if self.mode != "dense" else []
        if corpus:
            dense = [(i, s) for i, s in dense if self._is(ix.records[i], corpus)][:pool]
            lex = [(i, s) for i, s in lex if self._is(ix.records[i], corpus)][:pool]
        fused: dict[int, float] = {}
        for rank, (i, _) in enumerate(dense):
            fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank)
        for rank, (i, _) in enumerate(lex):
            fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank)
        dense_scores = dict(dense)
        hits = []
        for i, s in sorted(fused.items(), key=lambda x: -x[1])[:pool]:
            rec = dict(ix.records[i])
            rec.update({"library": lib, "score": s, "dense_score": dense_scores.get(i, 0.0)})
            hits.append(rec)
        return hits

    def retrieve(self, query: str, libs: list[str], k: int = 5, pool: int = 20, corpus: str | None = None) -> list[dict]:
        """corpus: 'grant' (HEC/PSF) | 'peer_review' (PeerRead/ICLR) | None = both."""
        qvec = self.embedder.embed([query])[0]
        hits = []
        for lib in libs:
            if lib in self.indexes:
                hits += self._search_one(lib, query, qvec, pool, corpus)
        hits.sort(key=lambda h: -h["score"])
        hits = hits[:pool]
        if self.mode == "hybrid_rerank" and hits:
            return self.reranker.rerank(query, hits, k)
        return hits[:k]
