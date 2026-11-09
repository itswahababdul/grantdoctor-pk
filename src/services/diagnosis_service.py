"""Proposal diagnosis: validate input, score risk factors, attach evidence and fixes."""
import json
import os
import tempfile

from src.analysis.hec_rules_checker import evaluate as hec_evaluate
from src.analysis.improvement_suggester import suggest
from src.analysis.rejection_diagnoser import diagnose
from src.ingestion.pdf_parser import pdf_to_text, split_sections
from src.services.runtime import get_runtime

REQUIRED = ["title", "abstract"]
NUMERIC = ["budget", "duration_months", "pi_publications", "similarity_index_pct", "ai_content_pct",
           "pi_contract_months", "pi_active_nrpu_grants", "pi_previous_delay_years"]
BOOLEAN = ["has_industry_collaboration", "industry_contribution", "oric_endorsed"]
EMPTY = (None, "", "(not sure)", "(not given)", "Not given")


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if v in EMPTY:
        return None
    return str(v).strip().lower() in ("yes", "true", "1", "y")


def normalize(proposal: dict) -> tuple[dict, list[str]]:
    """Clean user input; return (proposal, problems)."""
    p, problems = dict(proposal), []
    for k in REQUIRED:
        if not str(p.get(k) or "").strip():
            problems.append(f"'{k}' is required.")
    for k in BOOLEAN:
        p[k] = _to_bool(p.get(k))
    for k in ("research_domain", "pi_qualification"):
        if p.get(k) in EMPTY:
            p[k] = None
    for k in NUMERIC:
        v = p.get(k)
        if v in (None, ""):
            p[k] = None
            continue
        try:
            p[k] = float(str(v).replace(",", ""))
        except ValueError:
            problems.append(f"'{k}' must be a number.")
            p[k] = None
    if p.get("duration_months") is not None:
        p["duration_months"] = int(p["duration_months"])
    for k in ("budget", "duration_months"):
        if p.get(k) == 0:
            p[k] = None
    return p, problems


def parse_upload(name: str, data: bytes) -> dict:
    """Accept a .json proposal or a .pdf (best-effort section split)."""
    if name.lower().endswith(".json"):
        return json.loads(data.decode("utf-8"))
    if name.lower().endswith(".pdf"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(data)
            path = f.name
        try:
            sections = split_sections(pdf_to_text(path))
        finally:
            os.unlink(path)
        return {"title": name.rsplit(".", 1)[0], **sections}
    raise ValueError("Upload a .json or .pdf file.")


def diagnose_proposal(proposal: dict, cfg: dict | None = None) -> dict:
    p, problems = normalize(proposal)
    if problems:
        return {"ok": False, "errors": problems}
    rt = get_runtime(cfg)
    report = diagnose(p, rt.retriever, rt.ref_stats, rt.cfg["priority_keywords"])
    risk = report["overall_risk"]
    report.update({
        "ok": True, "level": "Low" if risk < 0.35 else "Moderate" if risk < 0.55 else "High",
        "suggestions": suggest(report, top_n=5), "proposal": p, "hec": hec_evaluate(p),
    })
    return report
