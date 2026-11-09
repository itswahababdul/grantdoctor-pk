"""Hugging Face dataset Vidushee/iclr-rejected-papers-with-code-1k -> GrantDoctor schema (REJECTED side).

Needs internet access to huggingface.co (it was not reachable from the sandbox this module was written in,
so the column mapping is defensive and UNTESTED against the real file: run it once and check the printed columns).

    pip install datasets
    python -m src.app.cli hf-iclr
"""
import json
from pathlib import Path

DATASET = "Vidushee/iclr-rejected-papers-with-code-1k"
CANDIDATES = {
    "title": ["title", "paper_title"],
    "abstract": ["abstract", "summary"],
    "year": ["year", "venue_year"],
    "source_url": ["url", "paper_url", "forum", "link"],
    "code_url": ["code", "code_url", "github", "repo", "github_url"],
    "review_text": ["reviews", "review", "decision_comment", "meta_review"],
}


def _pick(row: dict, keys: list[str]):
    for k in keys:
        if k in row and row[k] not in (None, "", []):
            v = row[k]
            return v if isinstance(v, (str, int, float)) else json.dumps(v, ensure_ascii=False)
    return None


def map_row(row: dict, i: int) -> dict:
    m = {k: _pick(row, c) for k, c in CANDIDATES.items()}
    return {
        "project_id": f"HF-ICLRREJ-{i:05d}",
        "title": m["title"] or "", "abstract": m["abstract"] or "",
        "objectives": "", "methodology": "",
        "review_text": m["review_text"] or "",
        "has_code": bool(m["code_url"]), "code_url": m["code_url"],
        "field": "Machine Learning (ICLR)", "year": int(m["year"]) if str(m["year"] or "").isdigit() else None,
        "funder": "ICLR", "status": "rejected", "corpus": "peer_review",
        "source_url": m["source_url"] or f"hf://{DATASET}/{i}",
    }


def write_hf_iclr(raw_dir: str, split: str = "train") -> dict:
    from datasets import load_dataset  # lazy: optional dependency
    ds = load_dataset(DATASET, split=split)
    print("columns found:", ds.column_names)
    recs = [map_row(dict(r), i) for i, r in enumerate(ds)]
    recs = [r for r in recs if len(r["abstract"]) >= 50]
    raw = Path(raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    with open(raw / "hf_iclr_rejected.jsonl", "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"rejected": len(recs), "with_code": sum(r["has_code"] for r in recs)}
