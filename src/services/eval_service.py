"""Run / load the retrieval ablation (BM25 vs dense vs hybrid vs hybrid+rerank)."""
import json
from datetime import datetime, timezone

from src.config import abs_path, load_config
from src.evaluation.retrieval_metrics import ablation
from src.services.runtime import get_runtime


def golden_path():
    return abs_path("src/evaluation/golden_set.json")


def load_golden() -> list[dict]:
    p = golden_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _results_path(cfg):
    return abs_path(cfg["paths"]["processed_dir"]) / "eval_results.json"


def load_last(cfg: dict | None = None) -> dict | None:
    cfg = cfg or load_config()
    p = _results_path(cfg)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def run(cfg: dict | None = None, k: int = 5) -> dict:
    cfg = cfg or load_config()
    rt = get_runtime(cfg)
    golden = load_golden()
    res = {"k": k, "n_queries": len(golden), "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "results": ablation(rt.indexes, rt.embedder, golden, k) if golden else {}}
    with open(_results_path(cfg), "w") as f:
        json.dump(res, f, indent=2)
    return res
