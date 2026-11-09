"""Final quality pass: Ask chips, escaping of evidence, Diagnose persistence, empty states, failure paths, long text.

Data is faked wherever possible so these run without a Spark build; the two real-service tests skip when nothing is built.
"""
import pandas as pd
import pytest

from src.app import ui
from src.config import ROOT
from src.services import analytics_service, eval_service, library_service as lib, qa_service, runtime
from src.services import diagnosis_service as dx

AT = pytest.importorskip("streamlit.testing.v1").AppTest
pytest.importorskip("plotly")
EVIL = '<script>alert(1)</script><img src=x onerror=alert(2)> $x$'
LONG = "Supercalifragilistic" * 40  # one 800-character "word": must not be able to widen a card


def view(n):
    return str(ROOT / f"src/app/views/{n}.py")


def html(at):
    return " ".join(m.value for m in at.markdown)


@pytest.fixture
def ready(monkeypatch):
    monkeypatch.setattr(runtime, "is_built", lambda cfg=None: True)
    monkeypatch.setattr(analytics_service, "available", lambda cfg=None: True)
    monkeypatch.setattr(analytics_service, "meta", lambda cfg=None: {"n_approved": 1, "n_rejected_real": 0, "n_rejected_synthetic": 0})


# ----------------------------------------------------------------------------- Ask
def _result(question, evidence=None):
    ev = evidence if evidence is not None else [{
        "project_id": "A-1", "library": "approved", "section": "abstract", "title": EVIL, "field": "Water", "funder": "HEC",
        "year": "2020.0", "status": "approved", "degradation": None, "score": 0.5, "text": EVIL + " " + LONG}]
    return {"ok": True, "question": question, "libraries": ["approved"], "corpus": None, "answer": "An answer with $5 and <b>tags</b>.",
            "faithfulness": 1.0, "evidence": ev}


@pytest.fixture
def ask(ready, monkeypatch):
    calls = []
    monkeypatch.setattr(qa_service, "ask", lambda q, libs=None, k=None, cfg=None: calls.append(q) or _result(q))
    at = AT.from_file(view("ask"), default_timeout=30).run()
    at.calls = calls
    return at


def test_ask_starts_with_empty_state(ask):
    assert not ask.exception and "No questions yet" in html(ask) and ask.calls == []


def test_ask_example_chip_runs_the_question(ask):
    ask.button(key="ask_ex_2").click().run()
    assert not ask.exception
    assert ask.calls == ["What funded work exists on groundwater?"]
    assert ask.text_input(key="ask_input").value == "What funded work exists on groundwater?"   # box shows what was asked
    assert "Q: What funded work exists on groundwater?" in html(ask) and "No questions yet" not in html(ask)
    ask.run()                                                    # a plain rerun must not ask again, and must keep the answer
    assert len(ask.calls) == 1 and "Grounding score" in html(ask)


def test_ask_typed_question_and_too_short_error(ask, monkeypatch):
    ask.text_input(key="ask_input").set_value("solar efficiency")      # a form only commits its value on submit,
    [b for b in ask.button if b.label == "Ask"][0].click().run()      # so set and submit in the same run
    assert not ask.exception and ask.calls == ["solar efficiency"]


def test_ask_evidence_text_is_escaped(ask):
    ask.button(key="ask_ex_0").click().run()
    h = html(ask)
    assert "<script" not in h and "<img" not in h and "onerror=alert(2)>" not in h
    assert "&lt;script&gt;" in h and "2020" in h and "2020.0" not in h        # year shown as an integer
    assert "\\$5" in h                                                         # "$" in an answer can never open a maths block


def test_ask_no_evidence_shows_empty_state(ready, monkeypatch):
    monkeypatch.setattr(qa_service, "ask", lambda q, libs=None, k=None, cfg=None: _result(q, evidence=[]))
    at = AT.from_file(view("ask"), default_timeout=30).run()
    at.button(key="ask_ex_1").click().run()
    assert not at.exception and "No evidence found" in html(at)


def test_ask_backend_failure_shows_friendly_error_not_a_traceback(ready, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("index is corrupt: /secret/path")
    monkeypatch.setattr(qa_service, "ask", boom)
    at = AT.from_file(view("ask"), default_timeout=30).run()
    at.button(key="ask_ex_0").click().run()
    assert not at.exception
    assert any("Something went wrong" in e.value for e in at.error) and not any("secret" in e.value for e in at.error)


# ----------------------------------------------------------------------------- Diagnose (real services, skipped if not built)
needs_build = pytest.mark.skipif(not runtime.is_built(), reason="libraries not built")


@needs_build
def test_diagnose_results_persist_across_reruns_real_services():
    at = AT.from_file(view("diagnose"), default_timeout=90).run()
    [b for b in at.button if "weak" in b.label][0].click(); at.run()
    [b for b in at.button if b.label == "Diagnose"][0].click(); at.run()
    assert not at.exception and "dx_report" in at.session_state
    first = at.session_state["dx_report"]["overall_risk"]
    at.run(); at.run()                                           # plain reruns (what a download click causes)
    assert "dx_report" in at.session_state and at.session_state["dx_report"]["overall_risk"] == first
    at.toggle(key="dx_table_view").set_value(True).run()         # a widget change reruns the script
    assert not at.exception and "dx_report" in at.session_state
    assert any(h.value.startswith("Step 2") for h in at.header)


def test_diagnose_service_rejects_garbage_without_raising():
    assert dx.normalize({})[1]                                   # problems are returned as a list, not raised


# ----------------------------------------------------------------------------- empty states, no raw exceptions
EMPTY_COLS = ["project_id", "title", "status", "field", "funder", "year", "budget", "duration_months", "abstract", "objectives",
              "methodology", "institute", "pi", "source_url", "grant_program", "avg_recommendation", "degradation"]


def test_explorer_with_an_empty_library(ready, monkeypatch):
    monkeypatch.setattr(lib, "load_projects", lambda cfg=None: pd.DataFrame(columns=EMPTY_COLS))
    at = AT.from_file(view("explorer"), default_timeout=30).run()
    assert not at.exception and "No projects match" in html(at) and "<b>0</b>" in html(at)


def test_explorer_long_unbroken_text_is_contained(ready, monkeypatch):
    df = pd.DataFrame([{c: None for c in EMPTY_COLS} | {"project_id": "L-1", "title": LONG, "status": "approved", "abstract": LONG,
                                                          "field": LONG, "funder": "HEC", "pi": LONG}])
    monkeypatch.setattr(lib, "load_projects", lambda cfg=None: df)
    at = AT.from_file(view("explorer"), default_timeout=30).run()
    assert not at.exception and LONG in html(at)
    assert "overflow-wrap:anywhere" in ui.CSS.replace(" ", "")  # the rule that stops long words widening cards


def test_trends_with_no_analytics_tables(ready, monkeypatch):
    monkeypatch.setattr(analytics_service, "table", lambda name, cfg=None: pd.DataFrame())
    at = AT.from_file(view("trends"), default_timeout=30).run()
    h = html(at)
    assert not at.exception and "No year data" in h and "No field data" in h and "No under-explored fields found" in h
    assert "No pilot-style projects found" in h and not at.get("plotly_chart")


def test_reasons_empty_and_filled(ready, monkeypatch):
    monkeypatch.setattr(analytics_service, "table", lambda name, cfg=None: pd.DataFrame())
    at = AT.from_file(view("reasons"), default_timeout=30).run()
    assert not at.exception and "No reviewer data in this build" in html(at)
    t = pd.DataFrame({"reason": ["novelty", "overclaiming"], "rate_rejected": [0.6, 0.3], "rate_accepted": [0.4, 0.2], "lift": [1.5, 1.4],
                      "p_value": [0.001, 0.01], "significant_bonferroni": [True, False], "covered_by_hidden_factor": [None, None],
                      "grant_analogue": ["a", EVIL], "suggested_fix": ["f", "g"], "not_addressed_by_grantdoctor": [True, True]})
    monkeypatch.setattr(analytics_service, "table", lambda name, cfg=None: t)
    at = AT.from_file(view("reasons"), default_timeout=30).run()
    h = html(at)
    assert not at.exception and len(at.get("plotly_chart")) == 1 and "<script" not in h and "&lt;script&gt;" in h


def test_reasons_with_a_stale_table_asks_for_a_rebuild(ready, monkeypatch):
    stale = pd.DataFrame({"reason": ["novelty"], "rate_rejected": [0.6], "rate_accepted": [0.4], "lift": [1.5]})
    monkeypatch.setattr(analytics_service, "table", lambda name, cfg=None: stale)
    at = AT.from_file(view("reasons"), default_timeout=30).run()
    assert not at.exception and "out of date" in html(at)


def test_evaluation_with_no_golden_set_disables_run(ready, monkeypatch):
    monkeypatch.setattr(eval_service, "load_golden", lambda: [])
    monkeypatch.setattr(eval_service, "load_last", lambda cfg=None: None)
    at = AT.from_file(view("evaluation"), default_timeout=30).run()
    assert not at.exception and at.button(key="ev_run").disabled


def test_pages_not_built_show_the_build_panel_not_an_error(monkeypatch):
    monkeypatch.setattr(runtime, "is_built", lambda cfg=None: False)
    monkeypatch.setattr(analytics_service, "available", lambda cfg=None: False)
    for page in ("home", "ask", "explorer", "trends", "evaluation", "reasons"):
        at = AT.from_file(view(page), default_timeout=30).run()
        assert not at.exception, page


# ----------------------------------------------------------------------------- theme safety (dark mode, narrow screens)
def test_css_has_no_hardcoded_light_backgrounds():
    css = ui.CSS.lower().replace(" ", "")
    for bad in ("background:#fff", "background:white", "background-color:#fff", "background-color:white", "background:#fafafa"):
        assert bad not in css
    assert "var(--gl-surface)" in css


def test_charts_use_transparent_background_and_bottom_legend():
    import plotly.graph_objects as go
    fig = ui.style_fig(go.Figure(go.Bar(x=[1], y=[1])), "T")
    assert fig.layout.paper_bgcolor == "rgba(0,0,0,0)" and fig.layout.plot_bgcolor == "rgba(0,0,0,0)"
    assert fig.layout.legend.y < 0                                # below the plot: cannot collide with the title on a phone


# ----------------------------------------------------------------------------- explorer table styling
def test_project_table_formats_budget_and_colours_status():
    from src.services import display_service as ds
    df = pd.DataFrame({"project_id": ["a", "b"], "title": ["t", "u"], "status": ["approved", "rejected"], "budget": [1234567.0, None],
                       "year": [2022.0, None], "duration_months": [12.0, None], "field": ["f", "g"], "funder": ["HEC", "PSF"], "extra": [1, 2]})
    out = ds.style_projects(df, ["project_id", "title", "extra"]).to_html()
    assert "1,234,567" in out and "2022" in out and "2022.0" not in out
    assert "color: #0e8a7d" in out and "color: #b4233c" in out          # approved / rejected as coloured text
    assert "–" in out and "color: #9aa0a6" in out                       # missing values are quiet
    assert out.index("status") < out.index("budget") < out.index("field")   # status and budget come first
    assert "extra" in out
