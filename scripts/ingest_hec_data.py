"""Convert the browser-downloaded hec_data.json into GrantDoctor JSONL (data/raw/hec_rejected.jsonl, hec_approved.jsonl).

Usage: python scripts/ingest_hec_data.py [path/to/hec_data.json]
"""
import json, re, sys, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "hec_data.json"


def rows_of(o):
    best, st = [], [o]
    while st:
        x = st.pop()
        if isinstance(x, list):
            if x and isinstance(x[0], dict) and len(x) > len(best):
                best = x
            st.extend(x[:3])
        elif isinstance(x, dict):
            st.extend(x.values())
    return best


def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip(" :\t\n")


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    years = {str(b["value"]): int(re.search(r"20\d\d", b["label"]).group()) for b in rows_of(d["batches"])}
    out = {"rejected": [], "approved": []}
    for status in out:
        for bid, payload in d[status].items():
            for r in rows_of(payload):
                digest, summary = clean(r.get("projectDigest")), clean(r.get("projectSummary"))
                abstract = digest if len(digest) >= len(summary) else summary
                dur = str(r.get("duration") or "")
                pno = str(r.get("projectNumber") or hashlib.md5(json.dumps(r, sort_keys=True).encode()).hexdigest()[:8])
                extra = {k: clean(r[k]) for k in ("bestSuited", "impactWithinTimeframe", "scientificResearchChallengenge",
                                                  "researchTrackRecord", "localySocioEco", "sdgGoals", "prioritySector") if r.get(k)}
                out[status].append({
                    "project_id": f"HEC-{status[:3].upper()}-{years.get(bid)}-{pno}",
                    "title": clean(r.get("projectName")), "abstract": abstract,
                    "objectives": "", "methodology": "", "budget": None,
                    "duration_months": int(dur) if dur.isdigit() else None,
                    "pi": clean(r.get("piName")), "institute": clean(r.get("piUniversity")),
                    "field": clean(r.get("discipline")) or "Unknown", "theme": clean(r.get("theme")),
                    "year": years.get(bid), "funder": "HEC", "status": status, "corpus": "grant",
                    "grant_program": "NRPU", "review_text": "", "language": "en",
                    "source_url": "https://research.hec.gov.pk/", "meta_json": json.dumps(extra, ensure_ascii=False),
                })
    raw = ROOT / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for status, recs in out.items():
        (raw / f"hec_{status}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs), encoding="utf-8")
        print(status, len(recs))


if __name__ == "__main__":
    main()
