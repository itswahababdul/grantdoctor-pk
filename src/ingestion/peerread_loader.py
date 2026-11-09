"""PeerRead (allenai/PeerRead) -> GrantDoctor schema.

PeerRead is the only dataset in this project where we know BOTH the decision (accepted / rejected)
AND the reviewers' written reasons. It covers conference papers, not grants, so every record is
tagged corpus="peer_review" and kept apart from HEC/PSF grant analytics.
Only ICLR 2017 carries accept/reject labels; ACL 2017 and CoNLL 2016 have scored reviews but no
decision in the public release, so they are skipped unless include_unlabelled=True.

    git clone --depth 1 https://github.com/allenai/PeerRead.git
    python -m src.app.cli peerread PeerRead/data
"""
import json
from pathlib import Path

CONFS = {"iclr_2017": ("ICLR", 2017), "acl_2017": ("ACL", 2017), "conll_2016": ("CoNLL", 2016)}


def _review_blob(reviews: list[dict]) -> tuple[str, str]:
    """Return (all reviewer text, meta-review text)."""
    body, meta = [], []
    for r in reviews:
        txt = (r.get("comments") or "").strip()
        if not txt:
            continue
        is_meta = str(r.get("IS_META_REVIEW", r.get("is_meta_review", ""))).lower() == "true"
        (meta if is_meta else body).append(txt)
    return "\n\n".join(body), "\n\n".join(meta)


def load_peerread(data_dir: str, include_unlabelled: bool = False) -> list[dict]:
    root = Path(data_dir)
    out = []
    for conf, (venue, year) in CONFS.items():
        for fp in sorted(root.glob(f"{conf}/*/reviews/*.json")):
            d = json.loads(fp.read_text(encoding="utf-8"))
            acc = str(d.get("accepted"))
            if acc not in ("True", "False") and not include_unlabelled:
                continue
            body, meta = _review_blob(d.get("reviews", []))
            ratings = []
            for r in d.get("reviews", []):
                try:
                    ratings.append(int(str(r.get("RECOMMENDATION", "")).strip()[:1]))
                except ValueError:
                    pass
            out.append({
                "project_id": f"PR-{venue}{year}-{d.get('id', fp.stem)}",
                "title": d.get("title", ""),
                "abstract": d.get("abstract", ""),
                "objectives": "", "methodology": "",
                "review_text": body, "meta_review": meta,
                "n_reviews": len([r for r in d.get("reviews", []) if (r.get("comments") or "").strip()]),
                "avg_recommendation": round(sum(ratings) / len(ratings), 2) if ratings else None,
                "field": f"Machine Learning / NLP ({venue})",
                "institute": None, "pi": d.get("authors"),
                "year": year, "funder": f"{venue}{year}",
                "status": "approved" if acc == "True" else "rejected" if acc == "False" else "unlabelled",
                "corpus": "peer_review",
                "source_url": f"peerread://{conf}/{fp.parent.parent.name}/{fp.stem}",
            })
    return out


def write_peerread(data_dir: str, raw_dir: str) -> dict:
    recs = load_peerread(data_dir)
    raw = Path(raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    counts = {}
    for status in ("approved", "rejected"):
        sub = [r for r in recs if r["status"] == status]
        with open(raw / f"peerread_{status}.jsonl", "w", encoding="utf-8") as f:
            for r in sub:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        counts[status] = len(sub)
    return counts
