"""Library explorer: sidebar filters -> count chip + styled table + CSV download -> two-column project detail card.

All project text is untrusted (scraped), so everything that goes into an unsafe_allow_html block is escaped with ui.esc.
"""
import streamlit as st

from src.app import ui
from src.services import display_service as ds
from src.services import library_service as lib

STATUS_LABEL = {"approved": ("Approved", "teal"), "rejected": ("Rejected", "danger"),
                "synthetic_rejected": ("Synthetic rejected", "warning")}


def _prose(label: str, text) -> str:
    body = ui.esc(text) if text else '<span class="gl-card-meta">Not recorded</span>'
    return f'<div class="gl-prose"><h4>{ui.esc(label)}</h4><div>{body}</div></div>'


def _facts(p: dict) -> str:
    year = None if p.get("year") is None else int(p["year"])
    dur = None if p.get("duration_months") is None else f"{int(p['duration_months'])} months"
    url = p.get("source_url") or ""
    link = (f'<a href="{ui.esc(url)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>'
            if url.startswith(("https://", "http://")) else None)
    rows = [("Field", ui.esc(p.get("field"))), ("Funder", ui.esc(p.get("funder"))), ("Year", ui.esc(year)),
            ("Budget", ui.esc(ui.fmt_pkr(p["budget"], compact=False)) if p.get("budget") else None),
            ("Duration", ui.esc(dur)), ("Principal investigator", ui.esc(p.get("pi"))),
            ("Institute", ui.esc(p.get("institute"))), ("Programme", ui.esc(p.get("grant_program"))),
            ("Avg reviewer rating", ui.esc(f"{p['avg_recommendation']:.1f}") if p.get("avg_recommendation") is not None else None),
            ("Source", link)]
    body = "".join(f'<div class="gl-fact-row"><div class="gl-fact-k">{k}</div><div class="gl-fact-v">{v}</div></div>'
                   for k, v in rows if v not in (None, "", "None"))
    return f'<div class="gl-fact">{body}</div>'


ui.page_header("Library explorer", "Browse the approved and rejected libraries separately.")
ui.require_ready()
ui.data_banner()

df = lib.load_projects()
with st.sidebar:
    st.markdown("**Filters**")
    group = st.radio("Library", list(lib.GROUPS), index=0, key="ex_group")
    funder = st.selectbox("Funder", lib.options(df, "funder"), key="ex_funder")
    field = st.selectbox("Field", lib.options(df, "field"), key="ex_field")
    ymin, ymax = (int(df["year"].min()), int(df["year"].max())) if df["year"].notna().any() else (2000, 2030)
    years = st.slider("Year", ymin, ymax, (ymin, ymax), key="ex_years") if ymin < ymax else None
    text = st.text_input("Search title/abstract", key="ex_text")

view = lib.filter_projects(df, group, funder, field, years, text)

# ----------------------------------------------------------------------------- result bar
c_chip, c_dl = st.columns([3, 1], vertical_alignment="center")
c_chip.markdown(ui.chip(f"{len(view):,}", f"of {len(df):,} projects match"), unsafe_allow_html=True)
c_dl.download_button("Download CSV", view[lib.COLUMNS].to_csv(index=False).encode("utf-8"),
                     "grantdoctor_projects_filtered.csv", "text/csv", icon=":material/download:", on_click="ignore",
                     width="stretch", disabled=view.empty, key="ex_dl")

if view.empty:
    ui.empty_state("No projects match these filters", "Widen the year range, or clear the search box.")
    st.stop()

st.dataframe(ds.style_projects(view, lib.COLUMNS), width="stretch", hide_index=True,
             column_config={"project_id": st.column_config.Column(width="medium"), "title": st.column_config.Column(width="large"),
                            "status": st.column_config.Column(width="small"),
                            "budget": st.column_config.NumberColumn("budget (PKR)", width="medium")})

# ----------------------------------------------------------------------------- project detail
ui.section("Project detail", "Pick a project from the filtered list.")
titles = dict(zip(view["project_id"], view["title"].fillna("Untitled")))
pid = st.selectbox("Open a project", list(titles), key="ex_pid",
                   format_func=lambda i: f"{i} · {str(titles[i])[:90]}")
p = lib.get_project(df, pid)
label, tone = STATUS_LABEL.get(p["status"], (str(p["status"]).title(), "neutral"))

with st.container(border=True):
    st.markdown(f'<div class="gl-detail-title">{ui.esc(p.get("title") or "Untitled")}</div>'
                f'<div class="gl-card-head gl-detail-head">{ui.badge(label, tone)}<span class="gl-card-meta">{ui.esc(p["project_id"])}</span></div>',
                unsafe_allow_html=True)
    if p.get("degradation"):
        ui.callout("warning", f"Synthetic degradations applied: {p['degradation']}")
    left, right = st.columns([2, 1])
    with left:
        st.markdown("".join(_prose(s.title(), p.get(s)) for s in ("abstract", "objectives", "methodology")),
                    unsafe_allow_html=True)
    with right:
        st.markdown(_facts(p), unsafe_allow_html=True)
