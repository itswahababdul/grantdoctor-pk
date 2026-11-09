"""Read precomputed Spark analytics (CSV/JSON written at build time)."""
import json

import pandas as pd

from src.config import abs_path, load_config

TABLES = ["funding_by_year_funder", "approval_rate_by_field", "field_profile",
          "underfunded_fields", "top_terms_by_field", "extension_candidates", "rejection_reasons"]


def _dir(cfg=None):
    cfg = cfg or load_config()
    return abs_path(cfg["paths"]["processed_dir"]) / "analytics"


def available(cfg=None) -> bool:
    return (_dir(cfg) / "meta.json").exists()


def meta(cfg=None) -> dict:
    with open(_dir(cfg) / "meta.json") as f:
        return json.load(f)


def table(name: str, cfg=None) -> pd.DataFrame:
    if name not in TABLES:
        raise KeyError(name)
    p = _dir(cfg) / f"{name}.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()
