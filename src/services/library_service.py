"""Browse/filter the approved and rejected libraries."""
import pandas as pd

from src.config import abs_path, load_config

GROUPS = {"Approved": ["approved"], "Rejected / synthetic-rejected": ["rejected", "synthetic_rejected"], "All": None}
COLUMNS = ["project_id", "title", "field", "funder", "year", "budget", "duration_months", "institute", "pi", "status"]


def load_projects(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    return pd.read_parquet(abs_path(cfg["paths"]["processed_dir"]) / "projects.parquet")


def filter_projects(df: pd.DataFrame, group: str = "All", funder: str | None = None, field: str | None = None,
                    years: tuple[int, int] | None = None, text: str = "") -> pd.DataFrame:
    out = df
    statuses = GROUPS.get(group)
    if statuses:
        out = out[out["status"].isin(statuses)]
    if funder and funder != "All":
        out = out[out["funder"] == funder]
    if field and field != "All":
        out = out[out["field"] == field]
    if years and "year" in out and out["year"].notna().any():
        out = out[out["year"].between(years[0], years[1]) | out["year"].isna()]
    if text.strip():
        t = text.strip().lower()
        blob = (out["title"].fillna("") + " " + out["abstract"].fillna("")).str.lower()
        out = out[blob.str.contains(t, regex=False)]
    return out


def get_project(df: pd.DataFrame, project_id: str) -> dict | None:
    row = df[df["project_id"] == project_id]
    return None if row.empty else {k: (None if pd.isna(v) else v) for k, v in row.iloc[0].to_dict().items()}


def options(df: pd.DataFrame, col: str) -> list[str]:
    return ["All"] + sorted(str(x) for x in df[col].dropna().unique())
