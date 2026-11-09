"""Download HEC's public rejected/approved project lists from research.hec.gov.pk (run on YOUR computer).

    pip install requests
    python scripts/fetch_hec_portal.py            # all batches, rejected + approved
    python scripts/fetch_hec_portal.py --only-rejected --batches 1 2

What it does
  1. GET  .../rga/getAllRgaBatch                      -> list of batches (YEAR 2020 ...)
  2. GET  .../rga/getRejectedProjectInformation/{id}  -> rejected projects of that batch (confirmed from your DevTools)
  3. GET  .../rga/getApprovedProjectInformation/{id}  -> GUESSED name; if it 404s, copy the real URL from DevTools
     (click "Approved Projects" on the site) and pass it with --approved-url-template.
Raw JSON of every call is saved in data/raw/hec_raw/ so nothing is lost, and a mapped GrantDoctor file is written to
data/raw/hec_rejected.jsonl / hec_approved.jsonl. Send me the printed "FIRST RECORD KEYS" block to finish the mapping.
Polite: one request at a time with a pause. Public pages only; no login, no cookies from your browser.
"""
import argparse
import json
import re
import time
from pathlib import Path

import requests

BASE = "https://research.hec.gov.pk/hec-rnd-rest/rest/rga"
ROOT = Path(__file__).resolve().parents[1]

FIELD_TOKENS = {  # GrantDoctor field -> substrings looked for in the JSON key names (lower-case)
    "source_pno": ["pno", "projectno", "projectid", "p_no", "proposalno"],
    "title": ["projectname", "projecttitle", "title", "name_of_project"],
    "pi": ["piname", "principal", "pi_name"],
    "institute": ["piuniversity", "university", "institute", "organization"],
    "field": ["discipline"],
    "theme": ["theme"],
    "abstract": ["abstract", "summary", "description"],
    "objectives": ["objective"],
    "methodology": ["methodolog"],
    "budget": ["budget", "amount", "cost", "grant_amount"],
    "duration_months": ["duration"],
    "remarks": ["remark", "comment", "reason", "reviewer"],
}


def get_json(sess, url):
    r = sess.get(url, timeout=120)
    r.raise_for_status()
    return r.json()


def find_list(obj):
    """The API may return a bare list or {data: [...]} / {result: [...]}; return the biggest list of dicts."""
    best = []
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, list):
            if o and isinstance(o[0], dict) and len(o) > len(best):
                best = o
            stack.extend(o[:3])
        elif isinstance(o, dict):
            stack.extend(o.values())
    return best


def pick(rec, tokens):
    for k, v in rec.items():
        kl = re.sub(r"[^a-z_]", "", str(k).lower())
        if any(t in kl for t in tokens) and v not in (None, "", []):
            return v
    return None


def map_record(rec, status, batch_label, grant_label):
    g = {f: pick(rec, t) for f, t in FIELD_TOKENS.items()}
    year = re.search(r"(20\d\d)", str(batch_label or ""))
    text_budget = str(g["budget"] or "").replace(",", "")
    return {
        "project_id": f"HEC-{status.upper()[:3]}-{batch_label}-{g['source_pno'] or abs(hash(json.dumps(rec, sort_keys=True))) % 10**8}".replace(" ", ""),
        "title": g["title"] or "", "abstract": g["abstract"] or g["title"] or "",
        "objectives": g["objectives"] or "", "methodology": g["methodology"] or "",
        "review_text": str(g["remarks"] or ""),
        "budget": float(text_budget) if re.fullmatch(r"\d+(\.\d+)?", text_budget) else None,
        "duration_months": int(g["duration_months"]) if str(g["duration_months"] or "").isdigit() else None,
        "pi": g["pi"], "institute": g["institute"],
        "field": g["field"] or "Unknown", "theme": g["theme"],
        "year": int(year.group(1)) if year else None, "funder": "HEC",
        "status": status, "corpus": "grant", "grant_program": grant_label,
        "source_url": "https://research.hec.gov.pk/#/rejected-projects" if status == "rejected" else "https://research.hec.gov.pk/",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", nargs="*", help="batch ids to fetch (default: all from getAllRgaBatch)")
    ap.add_argument("--only-rejected", action="store_true")
    ap.add_argument("--approved-url-template", default=BASE + "/getApprovedProjectInformation/{id}")
    ap.add_argument("--rejected-url-template", default=BASE + "/getRejectedProjectInformation/{id}")
    ap.add_argument("--pause", type=float, default=2.0)
    a = ap.parse_args()

    sess = requests.Session()
    sess.headers.update({"Accept": "application/json, text/plain, */*", "Referer": "https://research.hec.gov.pk/",
                         "User-Agent": "Mozilla/5.0 (GrantDoctor-PK student research project)"})
    sess.get("https://research.hec.gov.pk/", timeout=60)  # picks up the anonymous session cookie by itself
    raw_dir = ROOT / "data" / "raw" / "hec_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    batches = []
    try:
        bj = get_json(sess, BASE + "/getAllRgaBatch")
        (raw_dir / "batches.json").write_text(json.dumps(bj, ensure_ascii=False, indent=1))
        batches = find_list(bj)
        print("BATCH KEYS:", list(batches[0].keys()) if batches else "none found", "| n =", len(batches))
    except Exception as e:
        print("getAllRgaBatch failed:", e)
    def _bid(b):  # HEC batches look like {"label": "YEAR 2020", "value": 1}; "value" is the numeric ID
        return b.get("value") if b.get("value") is not None else pick(b, ["id", "batchid", "value"])
    ids = a.batches or [str(_bid(b)) for b in batches] or ["1"]
    labels = {str(_bid(b)): str(b.get("label") or pick(b, ["name", "batch", "title", "year"]) or "") for b in batches}

    out = {"rejected": [], "approved": []}
    for status, tmpl in [("rejected", a.rejected_url_template)] + ([] if a.only_rejected else [("approved", a.approved_url_template)]):
        for bid in ids:
            url = tmpl.format(id=bid)
            try:
                data = get_json(sess, url)
            except Exception as e:
                print(f"[{status} batch {bid}] FAILED {url} -> {e}")
                continue
            (raw_dir / f"{status}_batch_{bid}.json").write_text(json.dumps(data, ensure_ascii=False))
            rows = find_list(data)
            print(f"[{status} batch {bid}] {len(rows)} records")
            if rows and not out[status]:
                print(f"FIRST RECORD KEYS ({status}):", json.dumps(rows[0], ensure_ascii=False)[:1500])
            out[status] += [map_record(r, status, labels.get(bid) or f"batch{bid}", "NRPU") for r in rows]
            time.sleep(a.pause)

    for status, recs in out.items():
        if recs:
            p = ROOT / "data" / "raw" / f"hec_{status}.jsonl"
            p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs), encoding="utf-8")
            print("wrote", p, len(recs))


if __name__ == "__main__":
    main()
