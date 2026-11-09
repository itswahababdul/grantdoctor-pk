"""Why proposals get rejected: mined reviewer reasons (PeerRead). A paper-review proxy, not HEC/PSF decisions."""
import plotly.graph_objects as go
import streamlit as st

from src.analysis.review_reason_miner import unaddressed
from src.app import ui
from src.services import analytics_service as an

ui.page_header("Why proposals get rejected",
               "Mined from real reviewer text (PeerRead ICLR papers). A paper-review proxy, NOT HEC/PSF decisions.")
ui.require_ready()

t = an.table("rejection_reasons")
if t.empty:
    ui.empty_state("No reviewer data in this build",
                   "Run python -m src.app.cli peerread <PeerRead/data>, then rebuild the libraries.")
    st.stop()

NEEDED = {"reason", "rate_rejected", "rate_accepted", "lift", "p_value", "significant_bonferroni", "covered_by_hidden_factor",
          "grant_analogue", "suggested_fix", "not_addressed_by_grantdoctor"}
if not NEEDED.issubset(t.columns):   # an analytics file from an older build
    ui.empty_state("Reason data is out of date", "Rebuild the libraries (python -m src.app.cli build) to refresh it.")
    st.stop()

m = an.meta()
st.caption(f"{m.get('n_peer_review_rejected', 0)} rejected and {m.get('n_peer_review_accepted', 0)} accepted papers; "
           f"{m.get('n_reason_papers', 0)} have review text. Rule-based sentence matching: it shows what reviewers complain about, "
           "not why the committee decided.")

ui.section("Reasons raised more often for rejected papers")
view = t[["reason", "rate_rejected", "rate_accepted", "lift", "p_value", "significant_bonferroni", "covered_by_hidden_factor"]]
st.dataframe(view.style.format({"rate_rejected": "{:.2f}", "rate_accepted": "{:.2f}", "lift": "{:.2f}", "p_value": "{:.4f}"}, na_rep="–"),
             hide_index=True, width="stretch")

plot = t.assign(label=t["reason"].str.replace("_", " ").str.title()).sort_values("lift")   # highest lift ends up on top
fig = go.Figure()
for col, name, color in (("rate_accepted", "Accepted papers", ui.PALETTE[0]), ("rate_rejected", "Rejected papers", ui.PALETTE[3])):
    fig.add_bar(y=plot["label"], x=plot[col], name=name, marker_color=color, orientation="h",
                hovertemplate="<b>%{y}</b><br>" + name + ": %{x:.0%} of papers<extra></extra>")
fig.update_layout(barmode="group", bargroupgap=0.08)
fig.update_xaxes(tickformat=".0%", title_text="Papers where reviewers raise it", showgrid=True, gridcolor="rgba(128,128,128,0.22)", range=[0, 1])
fig.update_yaxes(showgrid=False)
st.plotly_chart(ui.style_fig(fig, "How often reviewers raise each reason", height=max(380, 46 * len(plot) + 120)),
                width="stretch", config=ui.PLOT_CONFIG)
worst = plot.sort_values("lift", ascending=False).iloc[0]
st.caption(f"{worst['label']} has the highest lift: reviewers raise it {worst['lift']:.2f}x as often for rejected papers as for accepted ones.")

ui.section("Not addressed by GrantDoctor yet (possible hidden reasons)")
gap = unaddressed(t)
if gap.empty:
    ui.callout("success", "Every frequent reason maps to an existing hidden factor.")
else:
    cards = []
    for _, r in gap.iterrows():
        sig = "Significant" if r["significant_bonferroni"] else "Suggestive"
        cards.append(ui.card(str(r["reason"]).replace("_", " ").title(),
                             [f"{r['rate_rejected']:.0%} of rejected vs {r['rate_accepted']:.0%} of accepted papers.",
                              f"Grant analogue: {r['grant_analogue']}", f"Fix: {r['suggested_fix']}"],
                             badge=(sig, "info" if r["significant_bonferroni"] else "neutral"), tone="warning"))
    ui.grid(cards)
