"""Central config loader. Every module reads settings from here."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path=None) -> dict:
    p = Path(path) if path else ROOT / "config" / "settings.yaml"
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_schema() -> dict:
    with open(ROOT / "config" / "schema.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def abs_path(rel: str) -> Path:
    return ROOT / rel
