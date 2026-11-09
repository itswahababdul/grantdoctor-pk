"""Diagnose a proposal: input form -> report stored in session_state -> results rendered from session_state.

The report lives in st.session_state["dx_report"], so it survives every rerun (download click, toggle,
tab switch, widget change) until the user presses "Clear results" or runs a new diagnosis.
All dynamic text that goes into unsafe_allow_html blocks is escaped with ui.esc (html.escape + markdown/$ escaping).
"""
import datetime as dt
import html
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analysis.hec_rules_checker import load_rules
from src.analysis.hidden_factor_checker import FACTOR_BASIS
from src.app import report as rpt
from src.app import ui
from src.services import diagnosis_service as dx

R = load_rules()
WEAK = {"title": "Improve water things", "abstract": "We will study water and improve it for people.",
        "objectives": "1) a; 2) b; 3) c; 4) d; 5) e", "methodology": "Standard methods will be used.",
        "budget": 30000000, "duration_months": 30, "field": "Water Resources", "pi_publications": 1,
        "research_domain": "Natural and Emerging Sciences", "pi_qualification": "PhD", "similarity_index_pct": 25,
        "pi_contract_months": 24, "pi_active_nrpu_grants": 1, "pi_previous_delay_years": 0}
YN = ["Not given", "Yes", "No"]
STATUS = {"PASS": ("Pass", "success"), "FAIL": ("Fail", "danger"), "UNKNOWN": ("Need input", "info"), "IMPROVE": ("Improve", "warning")}
STATUS_ICON = {"PASS": "✅ pass", "FAIL": "❌ fail", "UNKNOWN": "❔ need input", "IMPROVE": "⚠️ improve"}
LEVEL_TONE = {"Low": "success", "Moderate": "warning", "High": "danger"}
KINDS = [("hard", "Hard rules", "Eligibility checks. A failure here usually stops a proposal at administrative scrutiny."),
         ("required", "Required content", "Sections and content HEC expects to see in the proposal."),
         ("preference", "Preferences", "Things HEC prefers or encourages. They improve a proposal but rarely disqualify it.")]
DISCLAIMER = ("This is a heuristic aid. The HEC check reads rules from the source documents (content rules use a keyword check) "
              "and the risk score comes from ten explainable factors. Neither predicts the real HEC or PSF decision.")

DX_CSS = """
<style class="gl-css">
.gl-steps{display:flex; flex-wrap:wrap; align-items:center; gap:0.6rem 0.8rem;}
.gl-stepchip{display:flex; align-items:center; gap:0.55rem; border:1px solid var(--gl-border); border-radius:999px; background:var(--gl-surface);
  padding:0.35rem 1rem 0.35rem 0.4rem; font-weight:600; font-size:0.92rem;
  border-color:color-mix(in srgb, var(--gl-tone, transparent) 45%, var(--gl-border));}
.gl-stepchip small{font-weight:500; opacity:0.66; font-size:0.78rem;}
.gl-stepnum{flex:none; width:1.55rem; height:1.55rem; border-radius:999px; background:var(--gl-tone, var(--gl-neutral)); color:#fff;
  font-size:0.82rem; display:inline-flex; align-items:center; justify-content:center;}
.gl-steps-arrow{opacity:0.35; font-size:1.1rem;}
.gl-verdict h3{margin:0.2rem 0 0.4rem 0; font-size:1.25rem; font-weight:650; letter-spacing:-0.01em; padding:0;}
.gl-verdict p{margin:0.3rem 0; line-height:1.5;} .gl-verdict .gl-small{font-size:0.84rem; opacity:0.66;}
.gl-rule{border-left-color:var(--gl-tone, var(--gl-neutral));}
.gl-rule-head{display:flex; flex-wrap:wrap; align-items:center; gap:0.2rem 0.6rem; line-height:1.4;}
.gl-rule-detail{font-size:0.92rem; margin-top:0.3rem; opacity:0.85;} .gl-rule-fix{font-size:0.92rem; margin-top:0.2rem;}
.gl-rule a, .gl-meta a{color:var(--gl-accent); text-decoration:none;} .gl-rule a:hover{text-decoration:underline;}
.gl-action{display:flex; gap:0.9rem; border:1px solid var(--gl-border); border-radius:var(--gl-radius); background:var(--gl-surface); padding:0.9rem 1.1rem;}
.gl-action-n{flex:none; width:1.9rem; height:1.9rem; border-radius:999px; background:var(--gl-accent); color:#fff; font-weight:650;
  display:inline-flex; align-items:center; justify-content:center;}
.gl-action-head{display:flex; flex-wrap:wrap; align-items:center; gap:0.2rem 0.6rem; margin-bottom:0.2rem;}
.gl-action-body{line-height:1.5; font-size:0.94rem;}
.gl-row-head{display:flex; flex-wrap:wrap; align-items:center; gap:0.2rem 0.55rem; line-height:1.4;}
</style>
"""


# ----------------------------------------------------------------------------- helpers
def _name(factor: str) -> str:
    return factor.replace("_", " ").title()


def _clear_results():
    st.session_state.pop("dx_report", None)


def _load_example():
    st.session_state.dx_form = WEAK


def _yn(f, key):
    v = f.get(key)
    return YN.index("Yes" if v is True else "No" if v is False else "Not given")


def _steps_html(rep) -> str:
    def chip(n, label, sub, tone=None):
        cls = f" gl-tone-{tone}" if tone else ""
        return f'<div class="gl-stepchip{cls}"><span class="gl-stepnum">{n}</span><span>{ui.esc(label)}</span><small>{ui.esc(sub)}</small></div>'

    if rep is None:
        a, b = chip(1, "Official HEC rules", "not run yet"), chip(2, "Risk factors", "not run yet")
    else:
        hec = rep["hec"]
        if hec["hard_failures"]:
            a = chip(1, "Official HEC rules", f"{len(hec['hard_failures'])} hard failure(s)", "danger")
        elif hec["hard_unknown"]:
            a = chip(1, "Official HEC rules", "inputs missing", "warning")
        else:
            a = chip(1, "Official HEC rules", "eligible", "success")
        b = chip(2, "Risk factors", f"{rep['level']} risk · {rep['overall_risk']:.2f}", LEVEL_TONE[rep["level"]])
    return f'<div class="gl-steps">{a}<span class="gl-steps-arrow" aria-hidden="true">→</span>{b}</div>'


def _gauge(risk: float, level: str):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(risk, 2), number={"valueformat": ".2f", "font": {"size": 42}},
        gauge={"axis": {"range": [0, 1], "tickvals": [0, 0.35, 0.55, 1], "ticktext": ["0", "0.35", "0.55", "1"]},
               "bar": {"color": ui.LEVEL_COLOR[level], "thickness": 0.3}, "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
               "steps": [{"range": [0, 0.35], "color": "rgba(14,138,125,0.20)"},
                         {"range": [0.35, 0.55], "color": "rgba(194,122,12,0.20)"},
                         {"range": [0.55, 1], "color": "rgba(180,35,60,0.20)"}]}))
    fig.update_layout(height=200, margin=dict(l=24, r=24, t=16, b=0), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def _factor_chart(factors: dict):
    rows = sorted(((k, v["risk"], v["note"]) for k, v in factors.items()), key=lambda r: r[1])  # largest ends on top
    fig = go.Figure(go.Bar(
        x=[r[1] for r in rows], y=[_name(r[0]) for r in rows], orientation="h",
        marker_color=[ui.LEVEL_COLOR[rpt.level_of(r[1])] for r in rows],
        text=[f"{r[1]:.2f}" for r in rows], textposition="outside", cliponaxis=False,
        customdata=[html.escape(str(r[2])) for r in rows],
        hovertemplate="<b>%{y}</b><br>risk %{x:.2f}<br>%{customdata}<extra></extra>"))
    fig.update_xaxes(range=[0, 1.1], tickvals=[0, 0.35, 0.55, 1], showgrid=True, zeroline=False)
    fig.update_layout(height=max(320, 36 * len(rows) + 40), margin=dict(l=8, r=30, t=8, b=8), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", bargap=0.35)
    return fig


def _rule_cards(rules: list) -> str:
    out = []
    for x in rules:
        label, tone = STATUS[x["status"]]
        url = x.get("source_url") or ""
        link = (f'<a href="{ui.esc(url)}" target="_blank" rel="noopener noreferrer">HEC source: {ui.esc(x["source"])} ↗</a>'
                if url.startswith(("https://", "http://")) else ui.esc(x.get("source")))
        fix = f'<div class="gl-rule-fix"><b>Fix:</b> {ui.esc(x["fix"])}</div>' if x.get("fix") else ""
        out.append(f'<div class="gl-evidence gl-rule gl-tone-{tone}">'
                   f'<div class="gl-rule-head">{ui.badge(label, tone)}<b>{ui.esc(x["id"])}</b><span>{ui.esc(x["title"])}</span></div>'
                   f'<div class="gl-rule-detail">{ui.esc(x["detail"])}</div>{fix}<div class="gl-meta">{link}</div></div>')
    return "".join(out)


def _action_card(i: int, s: dict):
    lvl = rpt.level_of(s["risk"])
    pill = ui.badge(f"{lvl} · {s['risk']:.2f}", ui.LEVEL_COLOR[lvl])
    st.markdown(f'<div class="gl-action"><div class="gl-action-n">{i}</div><div class="gl-action-body">'
                f'<div class="gl-action-head"><b>{ui.esc(_name(s["factor"]))}</b>{pill}</div>'
                f'<div><b>Why:</b> {ui.esc(s["why"])}</div><div><b>Fix:</b> {ui.esc(s["fix"])}</div></div></div>',
                unsafe_allow_html=True)


def _similar_cards(items: list, library: str) -> str:
    tone, cls = ("teal", "gl-approved") if library == "approved" else ("danger", "gl-rejected")
    out = []
    for x in items:
        if library == "approved":
            detail = ui.esc(x.get("title") or "")
        else:
            detail = f"Synthetic · {ui.esc(x['degradation'])}" if x.get("degradation") else "Real record"
        out.append(f'<div class="gl-evidence {cls}"><div class="gl-row-head">{ui.badge(library.capitalize(), tone)}'
                   f'<b>[{ui.esc(x["id"])}]</b></div><div class="gl-rule-detail">{detail}</div></div>')
    return "".join(out)


# ----------------------------------------------------------------------------- page header + progress indicator
ui.page_header("Diagnose a proposal",
               "Step 1: official HEC rule check. Step 2: explainable risk factors. Neither predicts the real decision.")
ui.require_ready()
ui.data_banner()
st.markdown(DX_CSS, unsafe_allow_html=True)
steps_slot = st.empty()          # filled at the end of the script, once we know whether a report exists

# ----------------------------------------------------------------------------- input
st.session_state.setdefault("dx_form", {})
f = st.session_state.dx_form
st.button("Load example weak proposal", icon=":material/science:", on_click=_load_example)

tab_form, tab_up = st.tabs(["Fill in the form", "Upload JSON / PDF"])
proposal = None
with tab_form:
    with st.form("dx"):
        with st.container(border=True):
            ui.section("Proposal text", "What reviewers read first. Risk factors are scored mostly from this text.")
            title = st.text_input("Title", f.get("title", ""), help="A short, specific title.")
            c1, c2 = st.columns(2)
            field = c1.text_input("Field (e.g. Water Resources)", f.get("field", ""),
                                  help="Used to compare your budget with approved projects in the same field.")
            domains = ["(not sure)"] + R["domains_2026_27"]
            domain = c2.selectbox("Research domain (2026-27 call)", domains,
                                  index=domains.index(f["research_domain"]) if f.get("research_domain") in domains else 0)
            abstract = st.text_area("Abstract", f.get("abstract", ""), height=120)
            objectives = st.text_area("Objectives (number them: 1) ... 2) ...)", f.get("objectives", ""),
                                      help="Numbered, measurable objectives are easier to check and to review.")
            methodology = st.text_area("Methodology", f.get("methodology", ""), height=120,
                                       help="Mention data source, sample size, methods and ethics where relevant.")
            t1, t2 = st.columns(2)
            sim = t1.text_input("Similarity index % (Turnitin)", "" if f.get("similarity_index_pct") is None else str(f["similarity_index_pct"]),
                                help="Run a similarity check first and enter the percentage. Leave empty if not run yet.")
            ai = t2.text_input("AI-content %", "" if f.get("ai_content_pct") is None else str(f["ai_content_pct"]),
                               help="Run an AI-content check and enter the percentage. Leave empty if not run yet.")

        with st.container(border=True):
            ui.section("Budget and timeline", "Numbers only. Commas are fine.")
            b1, b2 = st.columns(2)
            budget = b1.text_input("Budget (PKR)", str(f.get("budget", "") or ""), help="Total amount requested.")
            duration = b2.text_input("Duration (months)", str(f.get("duration_months", "") or ""))

        with st.container(border=True):
            ui.section("PI and eligibility", "Needed for the hard HEC eligibility rules. Leave blank if unknown: it is shown as 'need input', never guessed.")
            quals = ["(not given)"] + R["pi_qualifications"] + ["Other"]
            p1, p2 = st.columns(2)
            qual = p1.selectbox("PI qualification", quals,
                                index=quals.index(f["pi_qualification"]) if f.get("pi_qualification") in quals else 0)
            contract = p2.text_input("PI contract length remaining (months)", str(f.get("pi_contract_months", "") or ""),
                                     help="The contract must cover the whole project duration.")
            p3, p4, p5 = st.columns(3)
            active = p3.text_input("PI's other active NRPU grants (0 if none)",
                                   "" if f.get("pi_active_nrpu_grants") is None else str(int(f["pi_active_nrpu_grants"])))
            delay = p4.text_input("Delay on PI's previous projects, years (0 if none)",
                                  "" if f.get("pi_previous_delay_years") is None else str(f["pi_previous_delay_years"]))
            pubs = p5.text_input("PI publications (optional)", str(f.get("pi_publications", "") or ""),
                                 help="Only used by the track-record risk factor.")

        with st.container(border=True):
            ui.section("Industry and ORIC", "Industry links and your university's ORIC endorsement.")
            k1, k2, k3 = st.columns(3)
            ind = k1.selectbox("Industry collaborator?", YN, index=_yn(f, "has_industry_collaboration"),
                               help="Required for the Product, Process and Technology Development domain.")
            indc = k2.selectbox("Industry contribution (cash/in-kind)?", YN, index=_yn(f, "industry_contribution"),
                                help="Can allow a budget above the basic-research cap for applied projects.")
            oric = k3.selectbox("ORIC endorsement obtained?", YN, index=_yn(f, "oric_endorsed"))

        submit = st.form_submit_button("Diagnose", type="primary")
    if submit:
        proposal = {"title": title, "field": field, "abstract": abstract, "objectives": objectives,
                    "methodology": methodology, "budget": budget, "duration_months": duration, "pi_publications": pubs,
                    "research_domain": domain, "pi_qualification": qual, "pi_contract_months": contract,
                    "pi_active_nrpu_grants": active, "pi_previous_delay_years": delay,
                    "similarity_index_pct": sim, "ai_content_pct": ai,
                    "has_industry_collaboration": ind, "industry_contribution": indc, "oric_endorsed": oric}
with tab_up:
    st.caption("A JSON file can include the official-rule fields too (research_domain, pi_qualification, similarity_index_pct, ...).")
    up = st.file_uploader("Proposal file", type=["json", "pdf"])
    if up is not None and st.button("Diagnose uploaded file"):
        try:
            proposal = dx.parse_upload(up.name, up.getvalue())
        except Exception as e:
            st.error(f"Could not read file: {e}")

# ----------------------------------------------------------------------------- run -> store
if proposal is not None:
    with st.spinner("Analysing..."):
        new = dx.diagnose_proposal(proposal)
    if new["ok"]:
        new["generated_on"] = dt.date.today().isoformat()
        st.session_state["dx_report"] = new          # results are rendered from here on every rerun
    else:
        for e in new["errors"]:
            st.error(e)

rep = st.session_state.get("dx_report")
steps_slot.markdown(_steps_html(rep), unsafe_allow_html=True)

# ----------------------------------------------------------------------------- results (always from session_state)
if rep:
    hec = rep["hec"]
    st.divider()
    left, a1, a2, a3 = st.columns([2.2, 1.2, 1, 1])
    with left:
        ui.section("Results", f"{rep['proposal'].get('title') or 'Untitled proposal'} · {rep.get('generated_on', '')}")
    a1.download_button("Report (HTML)", rpt.build_html(rep), "grantdoctor_diagnosis_report.html", "text/html",
                       icon=":material/description:", on_click="ignore", width="stretch", key="dx_dl_html")
    a2.download_button("Data (JSON)", json.dumps(rep, indent=2, default=str), "diagnosis.json", "application/json",
                       icon=":material/data_object:", on_click="ignore", width="stretch", key="dx_dl_json")
    a3.button("Clear results", icon=":material/close:", on_click=_clear_results, width="stretch", key="dx_clear")

    # --- verdict banner
    with st.container(border=True):
        g, t = st.columns([1, 1.5], vertical_alignment="center")
        with g:
            st.plotly_chart(_gauge(rep["overall_risk"], rep["level"]), width="stretch", config={"displayModeBar": False})
        with t:
            if hec["hard_failures"]:
                elig = f"<b>{len(hec['hard_failures'])} hard HEC rule(s) failed.</b> Fix these before anything else."
            elif hec["hard_unknown"]:
                elig = f"No hard rule failed, but <b>{len(hec['hard_unknown'])}</b> could not be checked yet."
            else:
                elig = "<b>All hard HEC rules pass.</b>"
            top = ", ".join(_name(s["factor"]) for s in rep["suggestions"][:3])
            level_pill = ui.badge(f"{rep['level']} risk", ui.LEVEL_COLOR[rep["level"]])
            st.markdown(f'<div class="gl-verdict">{level_pill}'
                        f'<h3>Overall rejection risk {rep["overall_risk"]:.2f}</h3>'
                        f'<p>{elig}</p><p>Biggest risk factors: {ui.esc(top)}.</p>'
                        f'<p class="gl-small">Heuristic score from 10 explainable factors. It does not predict the real decision.</p></div>',
                        unsafe_allow_html=True)

    # --- step 1
    st.header("Step 1: Official HEC rules")
    if hec["hard_failures"]:
        st.error(f"**{len(hec['hard_failures'])} hard rule(s) failed.** HEC checks eligibility first (administrative scrutiny), "
                 "so these must be fixed before anything else.")
        for x in hec["hard_failures"]:
            st.markdown(f'<div class="gl-callout gl-tone-danger"><b>{ui.esc(x["id"])} · {ui.esc(x["title"])}</b><br>{ui.esc(x["detail"])}'
                        f'<br><b>Fix:</b> {ui.esc(x["fix"])}</div>', unsafe_allow_html=True)
    elif hec["hard_unknown"]:
        st.warning(f"No hard rule failed, but **{len(hec['hard_unknown'])}** could not be checked because inputs are missing. "
                   "Fill them in above and run again.")
    else:
        st.success("All hard HEC rules pass.")

    k = st.columns(4)
    with k[0]:
        ui.kpi_card("Pass", hec["n_pass"], "Rules satisfied")
    with k[1]:
        ui.kpi_card("Fail", hec["n_fail"], "Hard rules violated")
    with k[2]:
        ui.kpi_card("Need input", hec["n_unknown"], "Cannot be checked yet")
    with k[3]:
        ui.kpi_card("Improve", hec["n_improve"], "Content to strengthen")

    if st.toggle("Table view", key="dx_table_view", help="Show all rules in one sortable table instead of cards."):
        tbl = pd.DataFrame([{"id": x["id"], "type": x["kind"], "rule": x["title"], "result": STATUS_ICON[x["status"]],
                             "detail": x["detail"], "how to fix": x["fix"], "HEC source": x["source_url"]} for x in hec["rules"]])
        st.dataframe(tbl, hide_index=True, width="stretch",
                     column_config={"HEC source": st.column_config.LinkColumn("HEC source", display_text="open")})
    else:
        known = {k_ for k_, _, _ in KINDS}
        groups = KINDS + ([("other", "Other rules", "")] if any(x["kind"] not in known for x in hec["rules"]) else [])
        for kind, label, blurb in groups:
            rules = [x for x in hec["rules"] if (x["kind"] == kind if kind != "other" else x["kind"] not in known)]
            if not rules:
                continue
            c = {s: sum(1 for x in rules if x["status"] == s) for s in STATUS}
            summary = f"{label} ({len(rules)}) · {c['PASS']} pass · {c['FAIL']} fail · {c['UNKNOWN']} need input · {c['IMPROVE']} improve"
            with st.expander(summary, expanded=(kind == "hard" and bool(c["FAIL"] or c["UNKNOWN"]))):
                if blurb:
                    st.caption(blurb)
                st.markdown(_rule_cards(rules), unsafe_allow_html=True)
    st.caption(f"Rules read from HEC documents on {hec['verified_on']}. Content rules use a keyword check; confirm against your full template. "
               "Always re-check the current call.")

    # --- step 2
    st.header("Step 2: Risk factors (heuristic)")
    st.plotly_chart(_factor_chart(rep["factors"]), width="stretch", config={"displayModeBar": False})
    st.caption("Colour = severity: " + "  ".join(ui.badge(f"{lv} {rng}", ui.LEVEL_COLOR[lv])
               for lv, rng in (("Low", "< 0.35"), ("Moderate", "0.35 to 0.55"), ("High", ">= 0.55"))) + " "
               "· By rubric dimension: " + " · ".join(f"{ui.esc(d)} {v:.2f}" for d, v in rep["rubric"].items()),
               unsafe_allow_html=True)

    ui.section("Fix these first", "Ordered by risk. Start at 1.")
    for i, s in enumerate(rep["suggestions"], 1):
        _action_card(i, s)

    with st.expander("All 10 factors and what backs them"):
        t2 = pd.DataFrame([{"factor": k_, "risk": v["risk"], "note": v["note"], "basis": FACTOR_BASIS[k_]} for k_, v in rep["factors"].items()])
        st.dataframe(t2.sort_values("risk", ascending=False), hide_index=True, width="stretch",
                     column_config={"risk": st.column_config.ProgressColumn("risk", min_value=0, max_value=1, format="%.2f")})

    # --- evidence
    cl, cr = st.columns(2)
    with cl:
        ui.section("Closest approved projects", "What funded work like yours looks like.")
        if rep["similar_approved"]:
            st.markdown(_similar_cards(rep["similar_approved"], "approved"), unsafe_allow_html=True)
        else:
            ui.empty_state("None found")
    with cr:
        ui.section("Closest rejected cases", "Where similar proposals went wrong.")
        if rep["similar_rejected"]:
            st.markdown(_similar_cards(rep["similar_rejected"], "rejected"), unsafe_allow_html=True)
        else:
            ui.empty_state("None found")

    ui.callout("note", DISCLAIMER)
