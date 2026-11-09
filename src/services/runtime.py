"""Loads indexes + retriever once and caches them. All services/UI go through here."""
from dataclasses import dataclass
from pathlib import Path

from src.config import abs_path, load_config


@dataclass
class Runtime:
    cfg: dict
    retriever: object
    embedder: object
    indexes: dict
    ref_stats: dict


_CACHE: dict[str, Runtime] = {}


def _dirs(cfg):
    return abs_path(cfg["paths"]["index_dir"]), abs_path(cfg["paths"]["processed_dir"])


def is_built(cfg: dict | None = None) -> bool:
    cfg = cfg or load_config()
    idx, proc = _dirs(cfg)
    return (idx / "approved" / "records.json").exists() and (idx / "rejected" / "records.json").exists() \
        and (proc / "projects.parquet").exists()


def get_runtime(cfg: dict | None = None) -> Runtime:
    cfg = cfg or load_config()
    key = str(_dirs(cfg)[0])
    if key not in _CACHE:
        from src.pipeline import load_runtime
        retriever, embedder, indexes, stats = load_runtime(cfg)
        _CACHE[key] = Runtime(cfg, retriever, embedder, indexes, stats)
    return _CACHE[key]


def reset_runtime() -> None:
    _CACHE.clear()
