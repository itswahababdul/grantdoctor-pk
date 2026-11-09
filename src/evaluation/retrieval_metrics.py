"""Recall@k, MRR, nDCG@k over a golden set [{query, libs, relevant_ids}] (project-level relevance)."""
import math


def _ids(hits):
    seen, out = set(), []
    for h in hits:
        if h["project_id"] not in seen:
            seen.add(h["project_id"]); out.append(h["project_id"])
    return out


def recall_at_k(ranked, relevant, k):
    return len(set(ranked[:k]) & set(relevant)) / (len(relevant) or 1)


def mrr(ranked, relevant):
    for i, r in enumerate(ranked, 1):
        if r in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked, relevant, k):
    dcg = sum(1.0 / math.log2(i + 2) for i, r in enumerate(ranked[:k]) if r in relevant)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return dcg / ideal if ideal else 0.0


def evaluate(retriever, golden: list[dict], k: int = 5) -> dict:
    rs, ms, ns = [], [], []
    for g in golden:
        ranked = _ids(retriever.retrieve(g["query"], g.get("libs", ["approved", "rejected"]), k=50, pool=50))
        rel = set(g["relevant_ids"])
        rs.append(recall_at_k(ranked, rel, k)); ms.append(mrr(ranked, rel)); ns.append(ndcg_at_k(ranked, rel, k))
    n = len(golden) or 1
    return {f"recall@{k}": sum(rs) / n, "mrr": sum(ms) / n, f"ndcg@{k}": sum(ns) / n}


def ablation(indexes, embedder, golden, k=5) -> dict:
    from src.retrieval.hybrid_retriever import HybridRetriever
    return {m: evaluate(HybridRetriever(indexes, embedder, mode=m), golden, k)
            for m in ["bm25", "dense", "hybrid", "hybrid_rerank"]}
