"""HEC rules & sources: source cards with open-link buttons, rules grouped by kind, search box filtering."""
from collections import Counter

import streamlit as st

from src.analysis.hec_rules_checker import load_rules
from src.app import ui
from src.services import display_service as ds

KINDS = {"hard": ("Hard rules (eligibility / thresholds)", "danger", "A failure here usually stops a proposal at administrative scrutiny."),
         "required": ("Required proposal content (policy section 3)", "info", "Sections and content HEC expects to see in the proposal."),
         "preference": ("What HEC prefers / encourages (strong-proposal traits)", "teal", "They improve a proposal but rarely disqualify it."),
         "other": ("Other rules", "neutral", "")}


def _rule_cards(rules: list, tone: str, sources: dict) -> str:
    out = []
    for r in rules:
        src = sources.get(r["source"], {})
        url = src.get("url") or ""
        link = (f'<a href="{ui.esc(url)}" target="_blank" rel="noopener noreferrer">{ui.esc(src.get("title", r["source"]))} ↗</a>'
                if url.startswith(("https://", "http://")) else ui.esc(src.get("title", r["source"])))
        fix = f'<div class="gl-card-body"><b>Fix:</b> {ui.esc(r["fix"])}</div>' if r.get("fix") else ""
        out.append(f'<div class="gl-evidence gl-toned gl-tone-{tone}"><div class="gl-card-head">{ui.badge(r["id"], tone)}'
                   f'<span class="gl-card-title">{ui.esc(r["title"])}</span></div>{fix}<div class="gl-card-meta">Source: {link}</div></div>')
    return "".join(out)


ui.page_header("HEC rules & sources", "Every official rule used by the checker, with the HEC document it comes from.")
R = load_rules()
ui.callout("note", f"Read from hec.gov.pk on {R['verified_on']}. Rules change between calls: always confirm in the current call document.")

# ----------------------------------------------------------------------------- sources
ui.section("Sources", "The HEC documents the rules were read from.")
used = Counter(r["source"] for r in R["rules"])
items = list(R["sources"].items())
for i in range(0, len(items), 3):
    for col, (sid, v) in zip(st.columns(3), items[i:i + 3]):
        with col, st.container(border=True):
            n = used.get(sid, 0)
            st.markdown(f'<div class="gl-src-title">{ui.esc(v["title"])}</div>'
                        f'<div class="gl-card-meta">Used by {n} rule{"" if n == 1 else "s"}</div>', unsafe_allow_html=True)
            if str(v.get("url", "")).startswith(("https://", "http://")):
                st.link_button("Open document", v["url"], icon=":material/open_in_new:", width="stretch")

# ----------------------------------------------------------------------------- rules
ui.section("Rules", "Grouped by kind. Type to filter by rule id, wording, fix or source.")
q = st.text_input("Search rules", key="rules_q", placeholder="e.g. budget, HEC-07, ethics, faq")
shown = ds.filter_rules(R["rules"], R["sources"], q)
st.markdown(ui.chip(f"{len(shown)} of {len(R['rules'])}", "rules"), unsafe_allow_html=True)

if not shown:
    ui.empty_state("No rules match your search", "Try a rule id such as HEC-07, or a single word from the rule title.")
for kind, rules in ds.group_rules(shown):
    label, tone, blurb = KINDS[kind]
    ui.section(f"{label} ({len(rules)})", blurb)
    st.markdown(_rule_cards(rules, tone, R["sources"]), unsafe_allow_html=True)

ui.section("Not found in public documents")
ui.callout("info", "The numeric scoring weights and minimum threshold used by the review panels were not in the public NRPU documents I read "
                   "(the policy only says proposals must pass a minimum threshold and are given merit scores). "
                   "The risk factors in Step 2 are therefore general heuristics, not HEC's scoring. "
                   "If you obtain the official evaluation form, add its criteria to config/hec_rules.yaml.")
