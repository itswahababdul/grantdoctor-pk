"""Trends & gaps: Plotly charts in the theme colours, each with a one-sentence insight computed from its own data.

Under-explored fields and extension ideas are card grids; the full table is one click away in an expander.
"""
import html

import plotly.graph_objects as go
import streamlit as st

from src.app import ui
from src.services import analytics_service as an
from src.services import display_service as ds

MAX_CARDS = 24

ui.page_header("Trends & gaps", "Computed with Spark at build time from the approved library.")
ui.require_ready()
ui.data_banner()

t1, t2, t3, t4 = st.tabs(["Funding over time", "Fields", "Under-explored", "Extension ideas"])

# ----------------------------------------------------------------------------- funding over time
with t1:
    raw = an.table("funding_by_year_funder")
    d, _ = ds.clean_funding(raw)
    if d.empty:
        ui.empty_state("No year data", "None of the approved projects has a year, so there is nothing to plot over time.")
    else:
        colors = ui.funder_colors(sorted(d["funder"].dropna().unique()))
        fig = go.Figure()
        for funder, g in d.groupby("funder"):
            fig.add_bar(x=g["year"], y=g["projects"], name=str(funder), marker_color=colors[funder],
                        hovertemplate="<b>%{x}</b> · %{fullData.name}<br>%{y} approved projects<extra></extra>")
        fig.update_layout(barmode="stack")
        fig.update_xaxes(dtick=1, tickformat="d")
        fig.update_yaxes(title_text="Approved projects")
        st.plotly_chart(ui.style_fig(fig, "Approved projects per year, by funder"), width="stretch", config=ui.PLOT_CONFIG)
        st.caption(ds.funding_insight(raw))

        b = d[d["total_budget"].notna() & (d["total_budget"] > 0)]
        if b.empty:
            ui.empty_state("No budget data", "The source records have no budget values to total.")
        else:
            log = st.toggle("Log scale", value=True, key="tr_log",
                            help="Budgets span several orders of magnitude, so a log axis keeps small years readable.")
            fig2 = go.Figure()
            for funder, g in b.groupby("funder"):
                fig2.add_scatter(x=g["year"], y=g["total_budget"], name=str(funder), mode="lines+markers",
                                 line=dict(color=colors[funder], width=3), marker=dict(size=8),
                                 hovertemplate="<b>%{x}</b> · %{fullData.name}<br>PKR %{y:,.0f}<extra></extra>")
            fig2.update_xaxes(dtick=1, tickformat="d")
            fig2.update_yaxes(title_text="Total budget (PKR)", tickformat="~s", type="log" if log else "linear",
                              **({"dtick": "D2", "minor": dict(showgrid=False)} if log else {}))
            st.plotly_chart(ui.style_fig(fig2, "Total approved budget over time, by funder"), width="stretch",
                            config=ui.PLOT_CONFIG)
            st.caption(ds.budget_insight(raw))

# ----------------------------------------------------------------------------- fields
with t2:
    ui.section("Field profile", "Approved projects, typical budget and duration for every field.")
    prof = an.table("field_profile")
    if prof.empty:
        ui.empty_state("No field data", "Field statistics appear once approved projects have a field.")
    else:
        pv = prof.style.format({"median_budget": "{:,.0f}", "avg_duration_months": "{:.1f}", "n_projects": "{:,.0f}"}, na_rep="–")
        st.dataframe(pv, hide_index=True, width="stretch", column_config={
            "n_projects": st.column_config.NumberColumn("projects"),
            "median_budget": st.column_config.NumberColumn("median budget (PKR)"),
            "avg_duration_months": st.column_config.NumberColumn("avg duration (months)")})

    terms = an.table("top_terms_by_field")
    if terms.empty:
        ui.empty_state("No term data", "Top terms appear here once abstracts have been analysed.")
    else:
        ui.section("Top terms", "The most frequent words in approved abstracts for one field.")
        fld = st.selectbox("Field", sorted(terms["field"].dropna().unique()), key="tr_field")
        top = terms[terms["field"] == fld].sort_values("count")
        fig3 = go.Figure(go.Bar(
            x=top["count"], y=top["term"], orientation="h", marker_color=ui.PALETTE[0],
            text=top["count"], textposition="outside", cliponaxis=False,
            customdata=[html.escape(str(f)) for f in top["field"]],
            hovertemplate="<b>%{y}</b><br>%{x} mentions in approved abstracts · %{customdata}<extra></extra>"))
        fig3.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.22)", title_text="Mentions")
        fig3.update_yaxes(showgrid=False)
        st.plotly_chart(ui.style_fig(fig3, f"Top terms in {fld}", height=max(300, 34 * len(top) + 90), legend=False),
                        width="stretch", config=ui.PLOT_CONFIG)
        st.caption(ds.terms_insight(terms, fld))

    with st.expander("Approval rate by field (demo metric if rejected data is synthetic)"):
        st.dataframe(an.table("approval_rate_by_field"), hide_index=True, width="stretch",
                     column_config={"approval_rate": st.column_config.ProgressColumn("approval rate", min_value=0, max_value=1, format="%.2f")})

# ----------------------------------------------------------------------------- under-explored
with t3:
    ui.section("Under-explored fields", "Fields in the lowest quartile of approved-project count: candidates for under-explored areas.")
    u = an.table("underfunded_fields")
    if u.empty:
        ui.empty_state("No under-explored fields found")
    else:
        u = u.sort_values("n_projects")
        cards = []
        for _, r in u.head(MAX_CARDS).iterrows():
            lines = []
            if r.get("median_budget") == r.get("median_budget") and r.get("median_budget") is not None:
                lines.append(f"Median budget: {ui.fmt_pkr(r['median_budget'])}")
            if r.get("avg_duration_months") == r.get("avg_duration_months") and r.get("avg_duration_months") is not None:
                lines.append(f"Average duration: {r['avg_duration_months']:.0f} months")
            cards.append(ui.card(str(r["field"]), lines or ["No budget or duration recorded for these projects."],
                                 badge=(f"{int(r['n_projects'])} projects", "warning"), tone="warning"))
        ui.grid(cards)
        st.caption(ds.underfunded_insight(u))
        with st.expander("Show as table"):
            st.dataframe(u, hide_index=True, width="stretch")

# ----------------------------------------------------------------------------- extension ideas
with t4:
    ui.section("Extension ideas", "Approved projects described as pilot / preliminary / proof-of-concept are natural scale-up follow-ups.")
    ext = an.table("extension_candidates")
    if ext.empty:
        ui.empty_state("No pilot-style projects found")
    else:
        cards = []
        for _, r in ext.head(MAX_CARDS).iterrows():
            yr = "" if r["year"] != r["year"] else f"{int(r['year'])}"
            cards.append(ui.card(str(r["title"]), [str(r["suggested_extension"])], badge=(yr, "teal") if yr else None, tone="teal",
                                 meta=f"{r['field']} · {r['project_id']}"))
        ui.grid(cards)
        if len(ext) > MAX_CARDS:
            st.caption(f"Showing {MAX_CARDS} of {len(ext)}. The full list is in the table below.")
        st.caption(ds.extension_insight(ext))
        with st.expander("Show as table"):
            st.dataframe(ext, hide_index=True, width="stretch")
