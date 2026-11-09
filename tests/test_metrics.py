from src.evaluation.retrieval_metrics import mrr, ndcg_at_k, recall_at_k


def test_metrics():
    ranked = ["x", "a", "b"]
    assert recall_at_k(ranked, {"a", "b"}, 2) == 0.5
    assert mrr(ranked, {"a"}) == 0.5
    assert 0 < ndcg_at_k(ranked, {"a"}, 3) <= 1
