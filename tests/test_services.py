from src.services import analytics_service as an
from src.services import diagnosis_service as dx
from src.services import eval_service as ev
from src.services import library_service as lib
from src.services import qa_service
from src.services.runtime import is_built


def test_built_and_meta(built_cfg):
    assert is_built(built_cfg) and an.available(built_cfg)
    m = an.meta(built_cfg)
    assert m["n_approved"] == 48 and m["n_rejected_synthetic"] == 48 and m["is_sample_data"] is True
    for t in an.TABLES:
        assert not an.table(t, built_cfg).empty or t in ("extension_candidates", "rejection_reasons")


def test_qa(built_cfg):
    r = qa_service.ask("which approved projects study solar panel efficiency?", cfg=built_cfg)
    assert r["ok"] and r["libraries"] == ["approved"] and r["evidence"]
    assert "[SAMPLE-A-" in r["answer"]
    assert not qa_service.ask("  ", cfg=built_cfg)["ok"]


def test_qa_rejected_route(built_cfg):
    r = qa_service.ask("why do vague proposals get rejected", cfg=built_cfg)
    assert r["libraries"] == ["rejected"]


def test_library_filters(built_cfg):
    df = lib.load_projects(built_cfg)
    assert len(lib.filter_projects(df, "Approved")) == 48
    assert len(lib.filter_projects(df, "Rejected / synthetic-rejected")) == 48
    w = lib.filter_projects(df, "Approved", field="Agriculture")
    assert set(w["field"]) == {"Agriculture"}
    assert lib.get_project(df, w.iloc[0]["project_id"])["title"]
    assert lib.get_project(df, "nope") is None


def test_diagnosis(built_cfg):
    weak = {"title": "x", "abstract": "We will study water.", "objectives": "1) a; 2) b; 3) c; 4) d; 5) e",
            "methodology": "Standard methods.", "budget": "30,000,000", "duration_months": "6", "field": "Water Resources"}
    r = dx.diagnose_proposal(weak, built_cfg)
    assert r["ok"] and r["level"] in ("Moderate", "High") and len(r["suggestions"]) == 5
    assert r["hec"]["n_fail"] >= 1 and not r["hec"]["eligible"]   # 6-month/30M weak proposal breaks the 20M cap
    bad = dx.diagnose_proposal({"title": "", "abstract": "", "budget": "abc"}, built_cfg)
    assert not bad["ok"] and len(bad["errors"]) >= 3


def test_parse_upload():
    assert dx.parse_upload("p.json", b'{"title":"t"}') == {"title": "t"}
    try:
        dx.parse_upload("p.txt", b"")
        assert False
    except ValueError:
        pass


def test_eval(built_cfg):
    res = ev.run(built_cfg)
    assert res["n_queries"] == 24 and set(res["results"]) == {"bm25", "dense", "hybrid", "hybrid_rerank"}
    assert ev.load_last(built_cfg)["ran_at"]
