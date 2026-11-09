"""Smoke-test every Streamlit page with AppTest. Skipped until the libraries are built (python -m src.app.cli build)."""
import pytest

from src.config import ROOT
from src.services.runtime import is_built

pytestmark = pytest.mark.skipif(not is_built(), reason="libraries not built")
AT = pytest.importorskip("streamlit.testing.v1").AppTest
VIEWS = ["ask", "explorer", "diagnose", "trends", "reasons", "evaluation", "about", "rules"]


@pytest.mark.parametrize("name", VIEWS)
def test_view_runs(name):
    at = AT.from_file(str(ROOT / f"src/app/views/{name}.py"), default_timeout=60).run()
    assert not at.exception


def test_entry_shows_kpis():
    at = AT.from_file(str(ROOT / "src/app/streamlit_app.py"), default_timeout=60).run()
    assert not at.exception and len(at.metric) == 4


def test_diagnose_shows_hec_failures():
    at = AT.from_file(str(ROOT / "src/app/views/diagnose.py"), default_timeout=60).run()
    [b for b in at.button if "weak" in b.label][0].click(); at.run()
    [b for b in at.button if b.label == "Diagnose"][0].click(); at.run()
    assert not at.exception
    assert any("hard rule" in e.value for e in at.error)
    assert any(h.value.startswith("Step 1") for h in at.header)
