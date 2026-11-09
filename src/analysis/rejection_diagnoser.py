"""Diagnose a proposal: hidden-factor risks -> rubric dimensions -> evidence from similar rejected cases."""
from src.analysis.hidden_factor_checker import check, overall_risk

RUBRIC = {
    "novelty": ["duplicate_overlap", "priority_alignment"],
    "methodology": ["data_sample_unclear", "ethics_missing", "deliverables_not_measurable"],
    "budget": ["budget_scope_mismatch"],
    "feasibility": ["timeline_unrealistic", "pi_track_record", "compliance_gaps"],
    "impact": ["commercialization_link", "priority_alignment"],
}


def diagnose(proposal: dict, retriever=None, ref_stats=None, priority_keywords=None) -> dict:
    text = " ".join(str(proposal.get(k) or "") for k in ("title", "abstract", "objectives"))
    max_sim, similar_rejected, similar_approved = None, [], []
    if retriever is not None:
        similar_approved = retriever.retrieve(text, ["approved"], k=3, corpus="grant")
        similar_rejected = (retriever.retrieve(text, ["rejected"], k=3, corpus="grant")
                            or retriever.retrieve(text, ["rejected"], k=3, corpus="peer_review"))
        if similar_approved:
            max_sim = max(h["dense_score"] for h in similar_approved)
    factors = check(proposal, ref_stats, max_sim, priority_keywords)
    rubric = {d: round(sum(factors[f]["risk"] for f in fs) / len(fs), 3) for d, fs in RUBRIC.items()}
    return {
        "overall_risk": overall_risk(factors),
        "rubric": rubric,
        "factors": factors,
        "similar_rejected": [{"id": h["project_id"], "degradation": h.get("degradation")} for h in similar_rejected],
        "similar_approved": [{"id": h["project_id"], "title": h.get("title")} for h in similar_approved],
    }
