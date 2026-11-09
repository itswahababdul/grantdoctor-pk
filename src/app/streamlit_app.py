"""Entry point:  streamlit run src/app/streamlit_app.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # so `import src...` works in every page

import streamlit as st  # noqa: E402

st.set_page_config(page_title="GrantDoctor-PK", page_icon=":material/search:", layout="wide")

from src.app import ui  # noqa: E402

ui.inject_css()

pages = [
    st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("views/ask.py", title="Ask the libraries", icon=":material/forum:"),
    st.Page("views/explorer.py", title="Library explorer", icon=":material/library_books:"),
    st.Page("views/diagnose.py", title="Diagnose a proposal", icon=":material/stethoscope:"),
    st.Page("views/rules.py", title="HEC rules & sources", icon=":material/gavel:"),
    st.Page("views/trends.py", title="Trends & gaps", icon=":material/trending_up:"),
    st.Page("views/reasons.py", title="Why rejected", icon=":material/help:"),
    st.Page("views/evaluation.py", title="Evaluation", icon=":material/science:"),
    st.Page("views/about.py", title="Data & ethics", icon=":material/balance:"),
]
st.navigation(pages).run()
