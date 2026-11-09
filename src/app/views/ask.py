"""Ask the libraries: example chips run a question straight away; every evidence field is escaped (it is scraped text)."""
import logging

import streamlit as st

from src.app import ui
from src.services import qa_service

log = logging.getLogger(__name__)
EXAMPLES = ["Which approved projects study solar panel efficiency?",
            "Why do proposals with vague objectives get rejected?",
            "What funded work exists on groundwater?"]


def _year(y):
    try:
        return int(float(y))
    except (TypeError, ValueError):
        return None


def _pick_example(text: str):
    st.session_state["ask_pending"] = text
    st.session_state["ask_input"] = text      # callbacks run before the widgets, so the box shows the example too


ui.page_header("Ask the libraries", "Answers come only from retrieved projects and always cite them.")
ui.require_ready()

st.session_state.setdefault("ask_history", [])
st.session_state.setdefault("ask_q", "")

with st.sidebar:
    scope = st.radio("Search in", list(qa_service.LIBRARY_CHOICES), index=0, key="ask_scope")
    top_k = st.slider("Evidence passages", 3, 10, 5, key="ask_topk")
    if st.button("Clear history", key="ask_clear"):
        st.session_state.ask_history = []

ui.section("Try an example", "One click runs the question.")
for col, ex in zip(st.columns(len(EXAMPLES)), EXAMPLES):
    col.button(ex, width="stretch", on_click=_pick_example, args=(ex,), key=f"ask_ex_{EXAMPLES.index(ex)}")

with st.form("ask_form"):
    q = st.text_input("Your question", value=st.session_state.ask_q, key="ask_input")
    go = st.form_submit_button("Ask", type="primary")

pending = st.session_state.pop("ask_pending", None)
question = pending if pending else (q if go else None)
if question is not None:
    st.session_state.ask_q = question
    try:
        with st.spinner("Searching..."):
            res = qa_service.ask(question, qa_service.LIBRARY_CHOICES[scope], top_k)
    except Exception:  # never show a traceback to the user
        log.exception("ask failed")
        res = {"ok": False, "error": "Something went wrong while searching the libraries. Please try again, or rebuild the libraries."}
    if not res["ok"]:
        st.error(res["error"])
    else:
        st.session_state.ask_history.insert(0, res)

if not st.session_state.ask_history:
    ui.empty_state("No questions yet", "Pick an example above or type your own question.")

for res in st.session_state.ask_history:
    with st.container(border=True):
        st.markdown(f'<div class="gl-card-title">Q: {ui.esc(res["question"])}</div>'
                    f'<div class="gl-card-meta">Searched: {ui.esc(", ".join(res["libraries"]))} · Grounding score: {res["faithfulness"]:.2f}</div>',
                    unsafe_allow_html=True)
        st.markdown(str(res["answer"]).replace("$", "\\$"))  # markdown stays, but "$" can never start a maths block
        with st.expander(f"Evidence ({len(res['evidence'])} passages)"):
            if not res["evidence"]:
                ui.empty_state("No evidence found", "Try different words, or search both libraries.")
            for e in res["evidence"]:
                ui.evidence_card(e["project_id"], e.get("title"), e["text"], library=e["library"], field=e.get("field"),
                                 funder=e.get("funder"), year=_year(e.get("year")), section=e.get("section"),
                                 score=e.get("score"), degradation=e.get("degradation"))
