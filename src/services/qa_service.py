"""Question answering over the two libraries."""
from src.evaluation.faithfulness_eval import faithfulness
from src.generation.guardrails import guard
from src.generation.llm_client import LLMClient
from src.generation.prompts import build_prompt
from src.retrieval.query_router import route, route_corpus
from src.services.runtime import get_runtime

LIBRARY_CHOICES = {"Auto (smart routing)": None, "Approved only": ["approved"],
                   "Rejected only": ["rejected"], "Both libraries": ["approved", "rejected"]}


def ask(question: str, libs: list[str] | None = None, top_k: int | None = None, cfg: dict | None = None) -> dict:
    question = (question or "").strip()
    if len(question) < 3:
        return {"ok": False, "error": "Please type a question (at least 3 characters)."}
    rt = get_runtime(cfg)
    c = rt.cfg
    libs = libs or route(question)
    k = top_k or c["retrieval"]["top_k"]
    corpus = route_corpus(question)
    hits = rt.retriever.retrieve(question, libs, k=k, pool=c["retrieval"]["candidate_pool"], corpus=corpus)
    llm = LLMClient(c["llm"]["provider"], c["llm"]["model"], c["llm"]["url"])
    try:
        raw = llm.generate(build_prompt(question, hits), hits)
    except Exception as e:  # LLM server down etc. -> degrade gracefully
        llm = LLMClient("extractive")
        raw = llm.generate("", hits) + f"\n\n(LLM unavailable, showing evidence only: {e.__class__.__name__})"
    answer = guard(raw, hits)
    return {
        "ok": True, "question": question, "libraries": libs, "corpus": corpus, "answer": answer,
        "faithfulness": round(faithfulness(answer, hits), 2) if hits else 0.0,
        "evidence": [{
            "project_id": h["project_id"], "library": h["library"], "section": h.get("section"),
            "title": h.get("title"), "field": h.get("field"), "funder": h.get("funder"),
            "year": h.get("year"), "status": h.get("status"), "degradation": h.get("degradation"),
            "score": round(float(h.get("rerank_score", h["score"])), 4), "text": h["text"],
        } for h in hits],
    }
