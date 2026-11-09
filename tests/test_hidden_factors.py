from src.analysis.hidden_factor_checker import check, overall_risk
from src.analysis.improvement_suggester import suggest

GOOD = {"abstract": "Dataset with sample size n = 300; ethical approval and consent; industry partner; water priority.",
        "objectives": "1) one; 2) two; 3) three", "methodology": "Milestones and two publications.",
        "budget": 5e6, "duration_months": 36, "field": "Water Resources", "pi_publications": 12}
BAD = {"abstract": "We will improve things.", "objectives": "1) a; 2) b; 3) c; 4) d; 5) e", "methodology": "",
       "budget": 3e7, "duration_months": 6, "field": "Water Resources"}
STATS = {"median_budget_by_field": {"Water Resources": 5e6}}


def test_bad_riskier_than_good():
    g, b = check(GOOD, STATS, 0.2, ["water"]), check(BAD, STATS, 0.9, ["water"])
    assert overall_risk(b) > overall_risk(g)
    assert b["ethics_missing"]["risk"] > g["ethics_missing"]["risk"]


def test_suggestions_ordered():
    rep = {"factors": check(BAD, STATS, 0.9, ["water"])}
    s = suggest(rep, 3)
    assert len(s) == 3 and s[0]["risk"] >= s[-1]["risk"]
