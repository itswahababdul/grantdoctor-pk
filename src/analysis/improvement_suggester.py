"""Turn the highest risks into concrete, ordered fixes."""
FIXES = {
    "budget_scope_mismatch": "Re-justify the budget line by line; align it with funded projects of similar scope.",
    "duplicate_overlap": "State explicitly how this differs from already-funded work; add a novelty paragraph.",
    "pi_track_record": "Add PI/co-PI publications, prior grants, and a collaborator with a strong record.",
    "priority_alignment": "Map the objectives to the national priority themes named in the call.",
    "ethics_missing": "Add an ethics/IRB/biosafety statement and consent procedure.",
    "timeline_unrealistic": "Add a Gantt chart; reduce the number of objectives or extend the duration.",
    "data_sample_unclear": "Specify data source, sample size, sampling method, and access permissions.",
    "commercialization_link": "Name end-users/industry partners and add a letter of support or pathway to impact.",
    "compliance_gaps": "Complete all required sections and annexures before submission.",
    "deliverables_not_measurable": "Define measurable deliverables (papers, prototypes, trained students) with dates.",
}


def suggest(report: dict, top_n: int = 5) -> list[dict]:
    ranked = sorted(report["factors"].items(), key=lambda kv: -kv[1]["risk"])[:top_n]
    return [{"factor": k, "risk": v["risk"], "why": v["note"], "fix": FIXES[k]} for k, v in ranked]
