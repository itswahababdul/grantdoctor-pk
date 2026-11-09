from src.analysis.hec_rules_checker import evaluate, load_rules
from src.services.diagnosis_service import normalize

GOOD = {"title": "t", "abstract": "A national problem in water; industry partner letter of support; students will be trained; novel approach; outcomes include a prototype and publication; sustainability plan beyond the grant; beneficiaries are farmers; interdisciplinary team.",
        "objectives": "1) one; 2) two", "methodology": "word " * 60 + " timeline with milestones and phases in months",
        "budget": 15e6, "duration_months": 24, "research_domain": "Product, Process and Technology Development",
        "pi_qualification": "PhD", "pi_contract_months": 30, "pi_active_nrpu_grants": 0, "pi_previous_delay_years": 0,
        "similarity_index_pct": 12, "ai_content_pct": 10, "has_industry_collaboration": True, "industry_contribution": True, "oric_endorsed": True}


def _by_id(rep):
    return {r["id"]: r for r in rep["rules"]}


def test_good_proposal_is_eligible():
    rep = evaluate(GOOD)
    assert rep["eligible"] and rep["n_fail"] == 0 and rep["n_unknown"] == 0


def test_each_hard_rule_can_fail():
    cases = {"HEC-01": {"duration_months": 25}, "HEC-02": {"budget": 21e6, "industry_contribution": False},
             "HEC-03": {"pi_qualification": "MSc"}, "HEC-04": {"pi_contract_months": 12},
             "HEC-05": {"pi_active_nrpu_grants": 1}, "HEC-06": {"pi_previous_delay_years": 3},
             "HEC-07": {"similarity_index_pct": 20}, "HEC-08": {"ai_content_pct": 26},
             "HEC-09": {"research_domain": "Made-up Domain"}, "HEC-10": {"has_industry_collaboration": False},
             "HEC-11": {"oric_endorsed": False}}
    for rid, change in cases.items():
        rep = evaluate({**GOOD, **change})
        assert _by_id(rep)[rid]["status"] == "FAIL", rid
        assert not rep["eligible"]


def test_boundaries_pass():
    rep = evaluate({**GOOD, "duration_months": 24, "budget": 20e6, "similarity_index_pct": 19, "ai_content_pct": 25})
    assert rep["eligible"]


def test_missing_inputs_are_unknown_not_guessed():
    rep = evaluate({"title": "t", "abstract": "x"})
    ids = _by_id(rep)
    assert ids["HEC-07"]["status"] == "UNKNOWN" and ids["HEC-03"]["status"] == "UNKNOWN"
    assert rep["eligible"] and len(rep["hard_unknown"]) >= 8


def test_budget_above_cap_ok_with_industry_contribution():
    assert _by_id(evaluate({**GOOD, "budget": 30e6}))["HEC-02"]["status"] == "PASS"


def test_every_rule_has_a_source():
    R = load_rules()
    for r in R["rules"]:
        assert r["source"] in R["sources"] and R["sources"][r["source"]]["url"].startswith("https://www.hec.gov.pk")


def test_normalize_handles_form_values():
    p, errs = normalize({"title": "t", "abstract": "a", "research_domain": "(not sure)", "pi_qualification": "(not given)",
                         "oric_endorsed": "Yes", "has_industry_collaboration": "Not given", "similarity_index_pct": "12.5",
                         "pi_active_nrpu_grants": "0", "budget": "1,000"})
    assert not errs and p["research_domain"] is None and p["oric_endorsed"] is True
    assert p["has_industry_collaboration"] is None and p["similarity_index_pct"] == 12.5
    assert p["pi_active_nrpu_grants"] == 0.0 and p["budget"] == 1000.0
