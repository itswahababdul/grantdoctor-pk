"""Diagnose page: results live in session_state and survive reruns. Retrieval is faked (no build/Spark needed)."""
import pytest

from src.analysis.hec_rules_checker import evaluate
from src.analysis.improvement_suggester import suggest
from src.analysis.rejection_diagnoser import diagnose
from src.app import report
from src.config import ROOT
from src.services import analytics_service, diagnosis_service as dx, runtime

AT = pytest.importorskip("streamlit.testing.v1").AppTest
pytest.importorskip("plotly")
EVIL = '<script>alert(1)</script><img src=x onerror=alert(2)> $x$'


def _fake_diag(proposal, cfg=None):
    p, problems = dx.normalize(proposal)
    if problems:
        return {"ok": False, "errors": problems}
    rep = diagnose(p, None, {}, [])
    risk = rep["overall_risk"]
    rep.update({"ok": True, "level": "Low" if risk < 0.35 else "Moderate" if risk < 0.55 else "High",
                "suggestions": suggest(rep, top_n=5), "proposal": p, "hec": evaluate(p),
                "similar_approved": [{"id": "A-1", "title": EVIL}],
                "similar_rejected": [{"id": "R-1", "degradation": "vague_objectives"}, {"id": "R-2", "degradation": None}]})
    return rep


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(runtime, "is_built", lambda cfg=None: True)
    monkeypatch.setattr(analytics_service, "available", lambda cfg=None: True)
    monkeypatch.setattr(analytics_service, "meta", lambda cfg=None: {"n_approved": 1, "n_rejected_real": 1, "n_rejected_synthetic": 0})
    monkeypatch.setattr(dx, "diagnose_proposal", _fake_diag)
    return AT.from_file(str(ROOT / "src/app/views/diagnose.py"), default_timeout=30).run()


def _diagnose(at):
    [b for b in at.button if "weak" in b.label][0].click(); at.run()
    [b for b in at.button if b.label == "Diagnose"][0].click(); at.run()
    return at


def _html(at):
    return " ".join(m.value for m in at.markdown)


def test_no_results_before_diagnose(app):
    assert not app.exception and "dx_report" not in app.session_state
    assert not any(h.value.startswith("Step 1") for h in app.header)


def test_results_survive_reruns(app):
    _diagnose(app)
    assert not app.exception and "dx_report" in app.session_state
    assert any("hard rule" in e.value for e in app.error)
    app.toggle(key="dx_table_view").set_value(True).run()          # a widget change reruns the script
    assert not app.exception and "dx_report" in app.session_state
    assert any(h.value.startswith("Step 1") for h in app.header) and any(h.value.startswith("Step 2") for h in app.header)
    app.run()                                                        # plain rerun (what a download click used to cause)
    assert any(h.value.startswith("Step 2") for h in app.header)


def test_clear_results(app):
    _diagnose(app)
    app.button(key="dx_clear").click(); app.run()
    assert "dx_report" not in app.session_state
    assert not any(h.value.startswith("Step") for h in app.header)


def test_invalid_input_shows_error_and_stores_nothing(app):
    [b for b in app.button if b.label == "Diagnose"][0].click(); app.run()
    assert "dx_report" not in app.session_state and any("required" in e.value for e in app.error)


def test_untrusted_text_is_escaped(app):
    _diagnose(app)
    html = _html(app)
    assert "<script" not in html and "<img" not in html and "&lt;script&gt;" in html


def test_html_report():
    rep = _fake_diag({"title": EVIL + " T", "abstract": "x", "budget": 30000000, "duration_months": 30})
    out = report.build_html(rep, generated_on="2026-11-01")
    assert "<script" not in out.split("<style>")[1].split("</style>")[1] and "&lt;script&gt;" in out
    assert "2026-11-01" in out and "Disclaimer" in out and "HEC-01" in out and "does not predict" in out
