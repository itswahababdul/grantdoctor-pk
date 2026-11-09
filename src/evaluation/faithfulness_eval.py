"""Cheap faithfulness proxy: share of answer sentences whose content words appear in the retrieved context.
(For the report: complement with manual / LLM-judge scoring on a sample.)"""
import re

from src.vectorstore.bm25_index import tokenize


def faithfulness(answer: str, contexts: list[dict], threshold: float = 0.6) -> float:
    ctx = set(tokenize(" ".join(c["text"] for c in contexts)))
    sents = [s for s in re.split(r"(?<=[.!?\n])\s+", answer) if len(tokenize(s)) >= 4]
    if not sents:
        return 0.0
    ok = 0
    for s in sents:
        toks = [t for t in tokenize(s) if len(t) > 3]
        if toks and sum(t in ctx for t in toks) / len(toks) >= threshold:
            ok += 1
    return ok / len(sents)
