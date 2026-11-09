"""Evaluation: ablation as a styled table (best per metric highlighted) and a grouped bar chart. The caveat is always visible."""
import plotly.graph_objects as go
import streamlit as st

from src.app import ui
from src.services import display_service as ds
from src.services import eval_service as ev

MODE_COLORS = {"BM25": "#3b6fb6", "Dense": "#c27a0c", "Hybrid": "#0e8a7d", "Hybrid + rerank": "#7a5bb5"}
BEST_BG = "background-color: rgba(14,138,125,0.32);"
CAVEAT = ("On the fictional sample data scores are near-perfect because the data is easy, and a small golden set cannot separate "
          "the retrieval modes. Report the numbers from your real data, and write your own golden questions.")


def _styled(tbl):
    """3 decimals, best value per metric highlighted and starred (the star keeps it readable without colour)."""
    best = tbl.max()
    fmt = {c: (lambda v, b=best[c]: f"{v:.3f} ★" if abs(v - b) < 1e-9 else f"{v:.3f}") for c in tbl.columns}
    return (tbl.rename(columns=ds.metric_label).style.format({ds.metric_label(c): f for c, f in fmt.items()})
            .apply(lambda s: [BEST_BG if abs(v - s.max()) < 1e-9 else "" for v in s], axis=0))


def _grouped_bar(tbl):
    metrics = [ds.metric_label(c) for c in tbl.columns]
    fig = go.Figure()
    for mode, row in tbl.iterrows():
        fig.add_bar(x=metrics, y=[row[c] for c in tbl.columns], name=str(mode), marker_color=MODE_COLORS.get(mode, ui.PALETTE[5]),
                    text=[f"{row[c]:.2f}" for c in tbl.columns], textposition="outside", textangle=-90, textfont_size=11, cliponaxis=False,
                    hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{y:.3f}<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.06)
    fig.update_yaxes(range=[0, 1.22], tickvals=[0, 0.2, 0.4, 0.6, 0.8, 1.0], title_text="Score (0 to 1)")
    return ui.style_fig(fig, "Retrieval quality by strategy", height=380)


ui.page_header("Evaluation", "Retrieval quality on a golden question set, with an ablation of the retrieval strategy.")
ui.require_ready()
ui.data_banner()

golden = ev.load_golden()
c1, c2 = st.columns([3, 1], vertical_alignment="center")
c1.markdown(ui.chip(len(golden), "golden questions") + ' <span class="gl-card-meta">src/evaluation/golden_set.json</span>',
            unsafe_allow_html=True)
if c2.button("Run ablation now", type="primary", disabled=not golden, icon=":material/play_arrow:", width="stretch", key="ev_run"):
    with st.spinner("Evaluating 4 retrieval modes..."):
        ev.run()

res = ev.load_last()
if res and res["results"]:
    tbl = ds.ablation_table(res["results"])
    ran = str(res["ran_at"]).replace("T", " ")[:16]
    st.caption(f"Last run: {ran} UTC  |  {res['n_queries']} queries  |  k={res['k']}")
    ui.section("Ablation table", "BM25 vs dense vs hybrid vs hybrid + rerank. ★ and green mark the best value per metric.")
    st.dataframe(_styled(tbl), width="stretch")
    st.plotly_chart(_grouped_bar(tbl), width="stretch", config=ui.PLOT_CONFIG)
    st.caption(ds.ablation_insight(tbl))
else:
    ui.empty_state("No evaluation run yet", "Press “Run ablation now” to compare the four retrieval modes.")
ui.callout("warning", CAVEAT)
