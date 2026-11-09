"""Pure helpers that turn analytics into display-ready text and filters. No Streamlit, no I/O.

Every caption is computed from the table it sits under, so it can never drift from the chart.
"""
import pandas as pd

MODE_LABELS = {"bm25": "BM25", "dense": "Dense", "hybrid": "Hybrid", "hybrid_rerank": "Hybrid + rerank"}
METRIC_LABELS = {"mrr": "MRR"}
KIND_LABELS = {"hard": "Hard rules", "required": "Required content", "preference": "Preferences", "other": "Other rules"}


def metric_label(key: str) -> str:
    if key in METRIC_LABELS:
        return METRIC_LABELS[key]
    if key.startswith("ndcg"):
        return "nDCG" + key[4:]
    if key.startswith("recall"):
        return "Recall" + key[6:]
    return key


def fmt_pkr(x, compact: bool = True) -> str:
    """'PKR 1.4B' (compact) or 'PKR 1,400,000,000'. Missing values give 'n/a'."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "n/a"
    if v != v:
        return "n/a"
    if compact:
        for lim, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
            if abs(v) >= lim:
                return f"PKR {v / lim:,.1f}{suf}"
    return f"PKR {v:,.0f}"


_money = fmt_pkr


# ----------------------------------------------------------------------------- trends
def clean_funding(d: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop rows without a year (they cannot be placed on a time axis). Returns (clean table, projects dropped)."""
    if d is None or d.empty:
        return pd.DataFrame(columns=["year", "funder", "projects", "total_budget"]), 0
    no_year = int(pd.to_numeric(d.loc[d["year"].isna(), "projects"], errors="coerce").fillna(0).sum())
    out = d[d["year"].notna()].copy()
    out["year"] = out["year"].astype(int)
    out["projects"] = pd.to_numeric(out["projects"], errors="coerce").fillna(0).astype(int)
    out["total_budget"] = pd.to_numeric(out["total_budget"], errors="coerce")
    return out, no_year


def funding_insight(d: pd.DataFrame) -> str:
    c, no_year = clean_funding(d)
    if c.empty:
        return ""
    by_year = c.groupby("year")["projects"].sum()
    peak, n = int(by_year.idxmax()), int(by_year.max())
    by_funder = c.groupby("funder")["projects"].sum().sort_values(ascending=False)
    total = int(by_funder.sum())
    top = by_funder.index[0]
    extra = f" ({no_year} more have no year and are not plotted)" if no_year else ""
    return (f"Approved projects peaked in {peak} with {n}; {top} accounts for {by_funder.iloc[0] / total:.0%} "
            f"of the {total} approved projects that have a year{extra}.")


def budget_insight(d: pd.DataFrame) -> str:
    c, _ = clean_funding(d)
    c = c[c["total_budget"].notna() & (c["total_budget"] > 0)]
    if c.empty:
        return "No budget totals are available in the source data."
    by_year = c.groupby("year")["total_budget"].sum()
    peak = int(by_year.idxmax())
    return (f"Recorded budget totals peak in {peak} at {_money(by_year.max())}; "
            "years or funders with no budget in the source are left out, and a few very large values can dominate a year.")


def terms_insight(terms: pd.DataFrame, field: str) -> str:
    t = terms[terms["field"] == field].sort_values("count", ascending=False)
    if t.empty:
        return ""
    top = [(str(r["term"]), int(r["count"])) for _, r in t.head(3).iterrows()]
    lead = f"In {field}, “{top[0][0]}” is the most frequent abstract term ({top[0][1]} mentions)"
    rest = top[1:]
    if not rest:
        return lead + "."
    if len({c for _, c in rest}) == 1:
        names = " and ".join(f"“{n}”" for n, _ in rest)
        tail = f"{names} follow with {rest[0][1]} each"
        tail = tail if rest[0][1] < top[0][1] else tail.replace(" follow with", " tie with it at")
    else:
        tail = "followed by " + " and ".join(f"“{n}” ({c})" for n, c in rest)
    return f"{lead}; {tail}."


def underfunded_insight(u: pd.DataFrame) -> str:
    if u is None or u.empty:
        return ""
    low = u.sort_values("n_projects").iloc[0]
    return (f"{len(u)} fields sit in the lowest quartile, with at most {int(u['n_projects'].max())} approved projects each; "
            f"{low['field']} has the fewest ({int(low['n_projects'])}).")


def extension_insight(e: pd.DataFrame) -> str:
    if e is None or e.empty:
        return ""
    vc = e["field"].value_counts()
    return (f"{len(e)} approved projects describe themselves as pilot or preliminary work; "
            f"{vc.index[0]} has the most ({int(vc.iloc[0])}).")


# ----------------------------------------------------------------------------- evaluation
def ablation_table(results: dict) -> pd.DataFrame:
    """Rows = retrieval modes (display names), columns = metric keys."""
    return pd.DataFrame(results).T.rename(index=MODE_LABELS)


def ablation_best(tbl: pd.DataFrame) -> dict:
    """metric -> list of modes holding the best value (ties keep every holder)."""
    out = {}
    for col in tbl.columns:
        best = tbl[col].max()
        out[col] = [m for m, v in tbl[col].items() if abs(v - best) < 1e-9]
    return out


def ablation_insight(tbl: pd.DataFrame) -> str:
    if tbl.empty:
        return ""
    best = ablation_best(tbl)
    n_modes, n_metrics = len(tbl.index), len(tbl.columns)
    if all(len(v) == n_modes for v in best.values()):
        return "All retrieval modes score the same on every metric, so this question set cannot tell them apart."
    wins = {m: [c for c, holders in best.items() if m in holders] for m in tbl.index}
    top_n = max(len(v) for v in wins.values())
    leaders = [m for m, v in wins.items() if len(v) == top_n]
    names = " and ".join(leaders)
    verb = "is" if len(leaders) == 1 else "are"
    stacked = tbl.stack()
    (low_mode, low_metric), low_val = stacked.idxmin(), stacked.min()
    return (f"{names} {verb} best on {top_n} of {n_metrics} metrics; the lowest score is {low_val:.3f} "
            f"({low_mode}, {metric_label(low_metric)}).")


# ----------------------------------------------------------------------------- rules
def filter_rules(rules: list[dict], sources: dict, query: str) -> list[dict]:
    """Every word of the query must appear in the rule's id, title, kind, fix text or source title (case-insensitive)."""
    words = (query or "").lower().split()
    if not words:
        return list(rules)
    out = []
    for r in rules:
        src = sources.get(r.get("source"), {}).get("title", "")
        blob = " ".join(str(x) for x in (r.get("id"), r.get("title"), r.get("kind"), r.get("fix"), src)).lower()
        if all(w in blob for w in words):
            out.append(r)
    return out


def group_rules(rules: list[dict], kinds=("hard", "required", "preference")) -> list[tuple[str, list[dict]]]:
    """[(kind, rules)] in display order; unknown kinds are collected under 'other'. Empty groups are dropped."""
    groups = [(k, [r for r in rules if r.get("kind") == k]) for k in kinds]
    groups.append(("other", [r for r in rules if r.get("kind") not in kinds]))
    return [(k, v) for k, v in groups if v]


# ----------------------------------------------------------------------------- explorer table
STATUS_TEXT_COLOR = {"approved": "#0e8a7d", "rejected": "#b4233c", "synthetic_rejected": "#c27a0c"}
TABLE_FIRST = ["project_id", "title", "status", "budget", "field", "funder", "year", "duration_months"]


def style_projects(view: pd.DataFrame, all_columns: list[str]):
    """Pandas Styler for the explorer table: budget with thousands separators, status as coloured text, quiet missing values."""
    cols = [c for c in TABLE_FIRST if c in view.columns] + [c for c in all_columns if c not in TABLE_FIRST and c in view.columns]
    sty = view[cols].style.format({"budget": "{:,.0f}", "year": "{:.0f}", "duration_months": "{:.0f}"}, na_rep="–")
    cell = getattr(sty, "map", None) or sty.applymap  # Styler.map needs pandas >= 2.1
    cell(lambda v: f"color: {STATUS_TEXT_COLOR[v]}; font-weight: 600;" if v in STATUS_TEXT_COLOR else "", subset=["status"])
    # Streamlit shows null cells as "None" whatever na_rep says, so at least make them quiet
    cell(lambda v: "color: #9aa0a6;" if v != v else "", subset=["budget", "year", "duration_months"])
    return sty
