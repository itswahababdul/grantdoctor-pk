"""Hidden-factor checker: 10 risk factors that are rarely stated in a rejection but often decide it.
Each factor returns risk in [0,1] (1 = high risk) plus a short note. Rule-based => explainable."""
import math
import re

FACTOR_WEIGHTS = {
    "budget_scope_mismatch": 1.2, "duplicate_overlap": 1.0, "pi_track_record": 0.8,
    "priority_alignment": 0.8, "ethics_missing": 0.9, "timeline_unrealistic": 1.0,
    "data_sample_unclear": 1.0, "commercialization_link": 0.6, "compliance_gaps": 1.1,
    "deliverables_not_measurable": 1.0,
}


# Which of my factors have an HEC document behind them (the rest are general grant-review heuristics).
FACTOR_BASIS = {
    "budget_scope_mismatch": "HEC-backed (20M cap, HEC-02) + heuristic benchmark",
    "duplicate_overlap": "Heuristic (HEC asks what the study delivers that would not otherwise happen)",
    "pi_track_record": "Heuristic (HEC eligibility looks at PI delays, not publications)",
    "priority_alignment": "HEC-backed (policy: alignment with national priorities)",
    "ethics_missing": "Heuristic (not listed in the NRPU documents I read)",
    "timeline_unrealistic": "HEC-backed (24-month maximum) + heuristic",
    "data_sample_unclear": "Heuristic (feasible methodology is an HEC criterion)",
    "commercialization_link": "HEC-backed (industry collaboration preferred)",
    "compliance_gaps": "HEC-backed (required proposal content)",
    "deliverables_not_measurable": "HEC-backed (outcomes must be identified)",
}


def _text(p: dict) -> str:
    return " ".join(str(p.get(k) or "") for k in ("title", "abstract", "objectives", "methodology")).lower()


def _has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.I) is not None


def check(proposal: dict, ref_stats: dict | None = None, max_similarity: float | None = None,
          priority_keywords: list[str] | None = None) -> dict:
    ref_stats = ref_stats or {}
    t = _text(proposal)
    out = {}

    # 1 budget vs typical approved budget for the same field
    med = (ref_stats.get("median_budget_by_field") or {}).get(proposal.get("field"))
    b = proposal.get("budget")
    if med and b:
        risk = min(1.0, abs(math.log(float(b) / med)) / math.log(3))
        out["budget_scope_mismatch"] = (risk, f"budget is {float(b)/med:.1f}x the approved median for this field")
    else:
        out["budget_scope_mismatch"] = (0.5, "budget or field benchmark missing")

    # 2 overlap with an already-funded project
    if max_similarity is None:
        out["duplicate_overlap"] = (0.3, "similarity to funded projects not computed")
    else:
        out["duplicate_overlap"] = (min(1.0, max(0.0, (max_similarity - 0.5) / 0.4)),
                                    f"closest approved project similarity = {max_similarity:.2f}")

    # 3 PI track record
    pubs = proposal.get("pi_publications")
    out["pi_track_record"] = ((0.5, "PI track record not provided") if pubs is None
                              else (0.1 if pubs >= 5 else 0.6, f"PI publications = {pubs}"))

    # 4 national priority alignment
    kws = priority_keywords or []
    hit = sum(1 for k in kws if k.lower() in t)
    out["priority_alignment"] = ((0.5, "no priority keywords configured") if not kws
                                 else (0.8 if hit == 0 else 0.3 if hit == 1 else 0.1, f"{hit} priority themes matched"))

    # 5 ethics / IRB / biosafety
    out["ethics_missing"] = ((0.1, "ethics statement present") if _has(t, r"ethic|irb|consent|biosafety|ethical")
                             else (0.7, "no ethics / consent / biosafety statement"))

    # 6 timeline realism = months per objective
    dur = proposal.get("duration_months")
    n_obj = max(1, len(re.split(r"[;\n]|\d\)|\d\.\s", proposal.get("objectives") or "")) - 1) if proposal.get("objectives") else 1
    if dur:
        per = dur / n_obj
        out["timeline_unrealistic"] = ((0.8, f"{per:.1f} months per objective is tight") if per < 4
                                       else (0.2, f"{per:.1f} months per objective"))
    else:
        out["timeline_unrealistic"] = (0.5, "duration missing")

    # 7 data / sample clarity
    out["data_sample_unclear"] = ((0.15, "sample/data source described") if _has(t, r"sample size|n\s*=|dataset|data source|survey of|respondents|samples? (will|were)")
                                  else (0.7, "sample size / data availability not clear"))

    # 8 commercialization / stakeholder link
    out["commercialization_link"] = ((0.2, "industry/policy link present") if _has(t, r"industry|commerci|patent|stakeholder|policy|startup|end[- ]user")
                                     else (0.6, "no industry/policy/end-user link"))

    # 9 compliance: required sections present
    missing = [k for k in ("abstract", "objectives", "methodology", "budget", "duration_months") if not proposal.get(k)]
    out["compliance_gaps"] = ((0.05, "all required sections present") if not missing
                              else (min(1.0, 0.3 + 0.2 * len(missing)), f"missing: {', '.join(missing)}"))

    # 10 measurable deliverables
    out["deliverables_not_measurable"] = ((0.15, "measurable deliverables mentioned") if _has(t, r"deliverable|milestone|publication|prototype|\bkpi\b|\d+\s+(papers|students|workshops|trials)")
                                          else (0.7, "no measurable deliverables / milestones"))

    return {k: {"risk": round(v[0], 3), "note": v[1]} for k, v in out.items()}


def overall_risk(factors: dict) -> float:
    tw = sum(FACTOR_WEIGHTS[k] for k in factors)
    return round(sum(FACTOR_WEIGHTS[k] * v["risk"] for k, v in factors.items()) / tw, 3)
