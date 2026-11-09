import pandas as pd

from src.embeddings.embedder import HashingEmbedder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.query_router import route
from src.vectorstore.approved_index import ApprovedIndex
from src.vectorstore.rejected_index import RejectedIndex


def _idx(cls, rows, emb):
    pdf = pd.DataFrame(rows)
    pdf["embedding"] = [v.tolist() for v in emb.embed(pdf["text"].tolist())]
    return cls().build_from_pandas(pdf)


def test_hybrid_finds_relevant():
    emb = HashingEmbedder()
    a = _idx(ApprovedIndex, [{"project_id": "A1", "text": "solar panel efficiency in Punjab"},
                             {"project_id": "A2", "text": "wheat yield under drought"}], emb)
    r = _idx(RejectedIndex, [{"project_id": "R1", "text": "vague study of good results"}], emb)
    ret = HybridRetriever({"approved": a, "rejected": r}, emb)
    hits = ret.retrieve("solar efficiency", ["approved"], k=1)
    assert hits[0]["project_id"] == "A1" and hits[0]["library"] == "approved"


def test_router():
    assert route("why was my proposal rejected") == ["rejected"]
    assert route("what funded projects exist on water") == ["approved"]
