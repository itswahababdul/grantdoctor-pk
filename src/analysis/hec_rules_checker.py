"""Checks a proposal against the OFFICIAL HEC NRPU rules in config/hec_rules.yaml.
Every rule carries its HEC source. Statuses:
  PASS     rule satisfied
  FAIL     hard rule violated (likely stopped at administrative scrutiny)
  UNKNOWN  needs an input the proposal did not provide (never guessed)
  IMPROVE  required/preferred content not found in the text (keyword check: confirm manually)
"""
import re
from functools import lru_cache

import yaml

from src.config import ROOT


@lru_cache(maxsize=1)
def load_rules() -> dict:
    with open(ROOT / "config" / "hec_rules.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _blob(p: dict) -> str:
    return " ".join(str(p.get(k) or "") for k in ("title", "abstract", "objectives", "methodology", "full_text")).lower()


def _num(p, k):
    v = p.get(k)
    return None if v in (None, "") else float(v)


# ---- each check returns (status, detail) ----
def max_duration(p, prm):
    d = _num(p, "duration_months")
    if d is None:
        return "UNKNOWN", "Duration not provided."
    return ("PASS", f"{d:.0f} months") if d <= prm["max_months"] else ("FAIL", f"{d:.0f} months is above the {prm['max_months']}-month maximum.")


def budget_cap(p, prm):
    b = _num(p, "budget")
    if b is None:
        return "UNKNOWN", "Budget not provided."
    if b <= prm["cap"]:
        return "PASS", f"PKR {b:,.0f} is within the PKR {prm['cap']:,} limit."
    if p.get("industry_contribution") is True:
        return "PASS", f"PKR {b:,.0f} is above PKR {prm['cap']:,}; allowed only for applied research with industry contribution (you declared one). Confirm in the call."
    return "FAIL", f"PKR {b:,.0f} is above PKR {prm['cap']:,} and no industry contribution was declared."


def pi_qualification(p, prm):
    q = p.get("pi_qualification")
    if not q:
        return "UNKNOWN", "PI qualification not provided."
    ok = q in load_rules()["pi_qualifications"]
    return ("PASS", q) if ok else ("FAIL", f"'{q}' is not one of {', '.join(load_rules()['pi_qualifications'])}.")


def pi_contract(p, prm):
    c, d = _num(p, "pi_contract_months"), _num(p, "duration_months")
    if c is None or d is None:
        return "UNKNOWN", "PI contract length or project duration not provided."
    return ("PASS", f"Contract {c:.0f} months covers {d:.0f}-month project.") if c >= d else ("FAIL", f"Contract ({c:.0f} months) is shorter than the project ({d:.0f} months).")


def one_grant(p, prm):
    n = _num(p, "pi_active_nrpu_grants")
    if n is None:
        return "UNKNOWN", "Number of the PI's other active NRPU grants not provided."
    return ("PASS", "No other active NRPU grant.") if n == 0 else ("FAIL", f"PI already holds {n:.0f} active NRPU grant(s).")


def previous_delay(p, prm):
    y = _num(p, "pi_previous_delay_years")
    if y is None:
        return "UNKNOWN", "Delay on the PI's previous projects not provided (enter 0 if none)."
    return ("PASS", f"Delay {y:g} years.") if y <= prm["max_years"] else ("FAIL", f"Previous project delayed {y:g} years (limit: {prm['max_years']}).")


def similarity(p, prm):
    s = _num(p, "similarity_index_pct")
    if s is None:
        return "UNKNOWN", "Run a similarity check (Turnitin) and enter the percentage."
    return ("PASS", f"{s:g}%") if s <= prm["max_pct"] else ("FAIL", f"{s:g}% is above the {prm['max_pct']}% limit.")


def ai_content(p, prm):
    a = _num(p, "ai_content_pct")
    if a is None:
        return "UNKNOWN", "Run an AI-content check and enter the percentage."
    return ("PASS", f"{a:g}%") if a <= prm["max_pct"] else ("FAIL", f"{a:g}% is above the {prm['max_pct']}% limit.")


def domain(p, prm):
    d = p.get("research_domain")
    if not d:
        return "UNKNOWN", "Research domain not selected."
    r = load_rules()
    if d in r["domains_2026_27"]:
        return "PASS", f"'{d}' is a domain of the 2026-27 call."
    if d in r["domains_2024_25"]:
        return "PASS", f"'{d}' belongs to the 2024-25 call; check it still exists in the current call."
    return "FAIL", f"'{d}' is not a listed NRPU domain."


def industry_for_product(p, prm):
    if p.get("research_domain") != "Product, Process and Technology Development":
        return "PASS", "Not in the Product/Process/Technology domain, so not mandatory."
    v = p.get("has_industry_collaboration")
    if v is None:
        return "UNKNOWN", "Industry collaboration not declared."
    return ("PASS", "Industry collaborator declared.") if v else ("FAIL", "This domain requires industry collaboration.")


def oric(p, prm):
    v = p.get("oric_endorsed")
    if v is None:
        return "UNKNOWN", "ORIC endorsement not declared."
    return ("PASS", "ORIC endorsement obtained.") if v else ("FAIL", "ORIC endorsement is required.")


def covers(p, prm):
    return ("PASS", "Found in text.") if re.search(prm["pattern"], _blob(p)) else ("IMPROVE", "Not found by keyword check (confirm in your full template).")


def method_detail(p, prm):
    n = len((p.get("methodology") or "").split())
    return ("PASS", f"{n} words.") if n >= prm["min_words"] else ("IMPROVE", f"Only {n} words of methodology.")


def objectives_clear(p, prm):
    obj = p.get("objectives") or ""
    n = len([x for x in re.split(r"[;\n]|\d\)|\d\.\s", obj) if x.strip()])
    return ("PASS", f"{n} objectives.") if n >= 2 else ("IMPROVE", "Fewer than two distinct objectives found.")


def industry_pref(p, prm):
    v = p.get("has_industry_collaboration")
    if v is None:
        return ("PASS", "Industry mentioned in text.") if re.search(r"industr|company|private sector", _blob(p)) else ("IMPROVE", "No industry link found.")
    return ("PASS", "Industry collaborator declared.") if v else ("IMPROVE", "No industry collaborator declared.")


CHECKS = {f.__name__: f for f in (max_duration, budget_cap, pi_qualification, pi_contract, one_grant, previous_delay,
                                  similarity, ai_content, domain, industry_for_product, oric, covers,
                                  method_detail, objectives_clear, industry_pref)}


def evaluate(proposal: dict) -> dict:
    cfg = load_rules()
    rows = []
    for r in cfg["rules"]:
        status, detail = CHECKS[r["check"]](proposal, r.get("params") or {})
        src = cfg["sources"][r["source"]]
        rows.append({"id": r["id"], "title": r["title"], "kind": r["kind"], "status": status, "detail": detail,
                     "fix": r["fix"] if status in ("FAIL", "IMPROVE", "UNKNOWN") else "",
                     "source": src["title"], "source_url": src["url"]})
    count = lambda s: sum(1 for x in rows if x["status"] == s)
    hard = [x for x in rows if x["kind"] == "hard"]
    return {
        "rules": rows,
        "hard_failures": [x for x in hard if x["status"] == "FAIL"],
        "hard_unknown": [x for x in hard if x["status"] == "UNKNOWN"],
        "n_pass": count("PASS"), "n_fail": count("FAIL"), "n_unknown": count("UNKNOWN"), "n_improve": count("IMPROVE"),
        "eligible": not any(x["status"] == "FAIL" for x in hard),
        "verified_on": cfg["verified_on"],
    }
