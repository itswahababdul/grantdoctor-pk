"""Explorer, trends, rules, evaluation, about: filters, escaping, charts, cards. Data is faked (no build/Spark needed)."""
import pandas as pd
import pytest

from src.config import ROOT
from src.services import analytics_service, eval_service, library_service as lib, runtime
from src.services import display_service as ds

AT = pytest.importorskip("streamlit.testing.v1").AppTest
pytest.importorskip("plotly")
EVIL = '<script>alert(1)</script><img src=x onerror=alert(2)> $x$'
VIEW = lambda n: str(ROOT / f"src/app/views/{n}.py")  # noqa: E731


def _html(at):
    return " ".join(m.value for m in at.markdown)


# ----------------------------------------------------------------------------- pure helpers
def test_ablation_best_keeps_ties_and_insight():
    tbl = ds.ablation_table({"bm25": {"recall@5": 1.0, "mrr": 0.9}, "hybrid": {"recall@5": 1.0, "mrr": 1.0},
                             "hybrid_rerank": {"recall@5": 0.9, "mrr": 1.0}})
    best = ds.ablation_best(tbl)
    assert best["recall@5"] == ["BM25", "Hybrid"] and best["mrr"] == ["Hybrid", "Hybrid + rerank"]
    s = ds.ablation_insight(tbl)
    assert s.startswith("Hybrid is best on 2 of 2") and "0.900" in s


def test_ablation_insight_all_equal():
    tbl = ds.ablation_table({"bm25": {"mrr": 1.0}, "dense": {"mrr": 1.0}})
    assert "cannot tell them apart" in ds.ablation_insight(tbl)


def test_funding_clean_and_insights():
    d = pd.DataFrame({"year": [None, 2021.0, 2022.0, 2022.0], "funder": ["PSF", "HEC", "HEC", "PSF"],
                      "projects": [5, 3, 4, 1], "total_budget": [None, 30e6, None, 20e6]})
    c, dropped = ds.clean_funding(d)
    assert dropped == 5 and list(c["year"]) == [2021, 2022, 2022]
    assert "peaked in 2022 with 5" in ds.funding_insight(d) and "5 more have no year" in ds.funding_insight(d)
    assert "2021" in ds.budget_insight(d) and "PKR 30.0M" in ds.budget_insight(d)
    assert ds.funding_insight(pd.DataFrame()) == ""


def test_filter_and_group_rules():
    src = {"s1": {"title": "Eligibility page"}}
    rules = [{"id": "HEC-01", "title": "Duration max 24 months", "kind": "hard", "fix": "Shorten it", "source": "s1"},
             {"id": "HEC-30", "title": "Mention ethics", "kind": "required", "fix": "Add ethics", "source": "s1"},
             {"id": "X-1", "title": "Odd", "kind": "weird", "fix": "", "source": "s1"}]
    assert [r["id"] for r in ds.filter_rules(rules, src, "ETHICS add")] == ["HEC-30"]
    assert [r["id"] for r in ds.filter_rules(rules, src, "eligibility")] == ["HEC-01", "HEC-30", "X-1"]
    assert ds.filter_rules(rules, src, "zzz") == []
    assert [k for k, _ in ds.group_rules(rules)] == ["hard", "required", "other"]


# ----------------------------------------------------------------------------- shared fakes
def _projects():
    base = {"abstract": "abs", "objectives": "obj", "methodology": "meth", "funder": "HEC", "field": "Water", "year": 2022.0,
            "budget": 1234567.0, "duration_months": 12.0, "institute": "Inst", "pi": "Dr X", "source_url": "https://example.org/a_b"}
    return pd.DataFrame([
        {**base, "project_id": "A-1", "title": EVIL, "status": "approved", "abstract": EVIL},
        {**base, "project_id": "R-1", "title": "Rejected one", "status": "rejected", "field": "Energy", "budget": None},
        {**base, "project_id": "S-1", "title": "Synthetic one", "status": "synthetic_rejected", "degradation": "vague_objectives"},
    ])


@pytest.fixture
def ready(monkeypatch):
    monkeypatch.setattr(runtime, "is_built", lambda cfg=None: True)
    monkeypatch.setattr(analytics_service, "available", lambda cfg=None: True)
    monkeypatch.setattr(analytics_service, "meta", lambda cfg=None: {"n_approved": 1, "n_rejected_real": 1, "n_rejected_synthetic": 1})


# ----------------------------------------------------------------------------- explorer
@pytest.fixture
def explorer(ready, monkeypatch):
    monkeypatch.setattr(lib, "load_projects", lambda cfg=None: _projects())
    return AT.from_file(VIEW("explorer"), default_timeout=30).run()


def test_explorer_count_chip_download_and_filter(explorer):
    assert not explorer.exception and "<b>1</b><span>of 3 projects match" in _html(explorer)   # default library: Approved
    assert len(explorer.get("download_button")) == 1
    explorer.sidebar.radio(key="ex_group").set_value("All").run()
    assert not explorer.exception and "<b>3</b><span>of 3 projects match" in _html(explorer)


def test_explorer_no_match_shows_empty_state(explorer):
    explorer.sidebar.text_input(key="ex_text").set_value("zzzz-nothing").run()
    assert not explorer.exception and "No projects match" in _html(explorer)


def test_explorer_detail_card_escapes_and_shows_facts(explorer):
    html = _html(explorer)
    assert "<script" not in html and "<img" not in html and "&lt;script&gt;" in html
    assert "PKR 1,234,567" in html and "12 months" in html and "Open source" in html and "Approved" in html
    explorer.sidebar.radio(key="ex_group").set_value("All").run()
    explorer.selectbox(key="ex_pid").set_value("S-1").run()
    html = _html(explorer)
    assert "Synthetic rejected" in html and "vague&#95;objectives" in html


# ----------------------------------------------------------------------------- trends
def _tables(name, cfg=None):
    return {
        "funding_by_year_funder": pd.DataFrame({"year": [None, 2021.0, 2022.0, 2022.0], "funder": ["PSF", "HEC", "HEC", "PSF"],
                                                "projects": [5, 3, 4, 1], "total_budget": [None, 3e7, 4e7, 2e7]}),
        "field_profile": pd.DataFrame({"field": ["Water", "Energy"], "n_projects": [9, 2], "median_budget": [1e6, None],
                                       "avg_duration_months": [12.0, 18.0]}),
        "top_terms_by_field": pd.DataFrame({"field": ["Water"] * 3, "term": ["river", "dam", "flow"], "count": [9, 5, 2], "rank": [1, 2, 3]}),
        "approval_rate_by_field": pd.DataFrame({"field": ["Water"], "approved": [9], "not_approved": [1], "approval_rate": [0.9]}),
        "underfunded_fields": pd.DataFrame({"field": ["Energy", EVIL], "n_projects": [2, 3], "median_budget": [None, 2e6],
                                            "avg_duration_months": [18.0, None]}),
        "extension_candidates": pd.DataFrame({"project_id": ["P-1"], "title": [EVIL], "field": ["Water"], "year": [2022.0],
                                              "suggested_extension": ["scale up"]}),
    }[name]


@pytest.fixture
def trends(ready, monkeypatch):
    monkeypatch.setattr(analytics_service, "table", _tables)
    return AT.from_file(VIEW("trends"), default_timeout=30).run()


def test_trends_has_three_plotly_charts_with_captions(trends):
    assert not trends.exception and len(trends.get("plotly_chart")) == 3
    caps = " ".join(c.value for c in trends.caption)
    assert "peaked in 2022" in caps and "Recorded budget totals" in caps and "“river” is the most frequent" in caps
    for old in ("bar_chart", "line_chart"):
        assert not trends.get(old)


def test_trends_cards_are_escaped_and_table_in_expander(trends):
    html = _html(trends)
    assert html.count('class="gl-grid"') == 2 and "<script" not in html and "&lt;script&gt;" in html
    assert "2 projects" in html and "scale up" in html
    assert any(e.label == "Show as table" for e in trends.expander)


def test_trends_term_field_and_log_toggle_rerun(trends):
    trends.toggle(key="tr_log").set_value(False).run()
    assert not trends.exception and len(trends.get("plotly_chart")) == 3


# ----------------------------------------------------------------------------- rules
def test_rules_sources_cards_and_search(ready):
    at = AT.from_file(VIEW("rules"), default_timeout=30).run()
    assert not at.exception and len(at.get("link_button")) == 5
    assert "28</b>" in _html(at) and "of 28" in _html(at)
    at.text_input(key="rules_q").set_value("HEC-07").run()
    assert "1 of 28" in _html(at) and "Similarity index" in _html(at) and "Required proposal content" not in _html(at)
    at.text_input(key="rules_q").set_value("zzzz-nothing").run()
    assert "No rules match" in _html(at)


# ----------------------------------------------------------------------------- evaluation
def test_evaluation_table_chart_and_caveat(ready, monkeypatch):
    res = {"k": 5, "n_queries": 3, "ran_at": "2026-11-01T00:00:00", "results": {
        "bm25": {"recall@5": 1.0, "mrr": 0.9, "ndcg@5": 0.95}, "dense": {"recall@5": 1.0, "mrr": 0.8, "ndcg@5": 0.9},
        "hybrid": {"recall@5": 1.0, "mrr": 1.0, "ndcg@5": 1.0}, "hybrid_rerank": {"recall@5": 1.0, "mrr": 1.0, "ndcg@5": 1.0}}}
    monkeypatch.setattr(eval_service, "load_golden", lambda: [{"query": "q"}])
    monkeypatch.setattr(eval_service, "load_last", lambda cfg=None: res)
    at = AT.from_file(VIEW("evaluation"), default_timeout=30).run()
    assert not at.exception and len(at.dataframe) == 1 and len(at.get("plotly_chart")) == 1
    spec = at.get("plotly_chart")[0].proto.spec.replace(" ", "")
    assert spec.count('"type":"bar"') == 4
    assert "data is easy" in _html(at)
    assert "Hybrid and Hybrid + rerank are best on 3 of 3" in " ".join(c.value for c in at.caption)


def test_evaluation_caveat_visible_without_results(ready, monkeypatch):
    monkeypatch.setattr(eval_service, "load_golden", lambda: [])
    monkeypatch.setattr(eval_service, "load_last", lambda cfg=None: None)
    at = AT.from_file(VIEW("evaluation"), default_timeout=30).run()
    assert not at.exception and "No evaluation run yet" in _html(at) and "data is easy" in _html(at)


# ----------------------------------------------------------------------------- about
def test_about_has_five_cards(ready):
    at = AT.from_file(VIEW("about"), default_timeout=30).run()
    html = _html(at)
    assert not at.exception and html.count('class="gl-card gl-tonebar') == 5
    for title in ("Approved library", "Rejected library", "Official HEC check", "Risk score", "Limitations"):
        assert title in html
