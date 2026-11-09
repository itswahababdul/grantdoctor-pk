import shutil

import pytest

from src.config import load_config


@pytest.fixture(scope="session")
def built_cfg(tmp_path_factory):
    """Build the whole system once on sample data into a temp folder (needs Java for Spark)."""
    if shutil.which("java") is None:
        pytest.skip("Java not installed")
    from scripts.make_sample_data import make
    from src.config import ROOT
    from src.pipeline import build
    from src.services.runtime import reset_runtime
    make()
    tmp = tmp_path_factory.mktemp("gl")
    raw = tmp / "raw"; raw.mkdir()
    shutil.copy(ROOT / "data/sample/approved.jsonl", raw / "approved.jsonl")
    cfg = load_config()
    cfg["paths"] = {"raw_dir": str(raw), "sample_dir": str(tmp), "processed_dir": str(tmp / "processed"), "index_dir": str(tmp / "index")}
    cfg["spark"]["shuffle_partitions"] = 2
    build(cfg=cfg)
    reset_runtime()
    return cfg
