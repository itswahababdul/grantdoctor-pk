"""Rejected-library data. Rejected proposals are NOT public, so two legal sources:
 1. load_proxy_rejected(): anonymized proposals supplied with permission (ORIC / seniors).
 2. make_synthetic_negatives(): controlled degradation of approved proposals, labelled `synthetic_rejected`.
Always disclose which one you used in the report.
"""
import glob
import json
import random
import re

DEGRADATIONS = ["inflate_budget", "vague_objectives", "drop_ethics", "shorten_timeline", "drop_methodology_detail"]


def load_proxy_rejected(directory: str) -> list[dict]:
    recs = []
    for fp in glob.glob(f"{directory}/*.jsonl"):
        with open(fp, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                r["status"] = "rejected"
                recs.append(r)
    return recs


def _drop_sentences(text: str, pattern: str) -> str:
    sents = re.split(r"(?<=[.!?])\s+", text or "")
    return " ".join(s for s in sents if not re.search(pattern, s, re.I))


def make_synthetic_negatives(approved: list[dict], seed: int = 42, per_record: int = 1) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for r in approved:
        for k in range(per_record):
            n = dict(r)
            applied = rng.sample(DEGRADATIONS, k=rng.randint(1, 3))
            if "inflate_budget" in applied and n.get("budget"):
                n["budget"] = float(n["budget"]) * rng.uniform(2.5, 4.0)
            if "vague_objectives" in applied:
                n["objectives"] = "To study and improve the situation and provide good results."
            if "drop_ethics" in applied:
                n["methodology"] = _drop_sentences(n.get("methodology", ""), r"ethic|irb|consent|biosafety")
                n["abstract"] = _drop_sentences(n.get("abstract", ""), r"ethic|irb|consent|biosafety")
            if "shorten_timeline" in applied and n.get("duration_months"):
                n["duration_months"] = max(3, int(n["duration_months"]) // 4)
            if "drop_methodology_detail" in applied:
                n["methodology"] = "Standard methods will be used."
            n["project_id"] = f"{r['project_id']}-SYN{k}"
            n["status"] = "synthetic_rejected"
            n["degradation"] = ",".join(applied)
            out.append(n)
    return out
