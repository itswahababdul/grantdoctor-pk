import streamlit as st

from src.app import ui
from src.services import analytics_service as an

ui.page_header("GrantDoctor-PK", "Research-proposal intelligence over HEC & Pakistan Science Foundation projects")

if not ui.is_ready():
    ui.build_panel()
    st.stop()

ui.data_banner()
m = an.meta()
c = st.columns(4)
c[0].metric("Approved projects", m.get("n_approved", 0))
c[1].metric("Rejected (real)", m.get("n_rejected_real", 0))
c[2].metric("Rejected (synthetic)", m.get("n_rejected_synthetic", 0))
c[3].metric("Fields covered", m.get("n_fields", 0))
st.caption(f"Funders: {', '.join(m.get('funders') or []) or 'n/a'}  |  Libraries built: {m.get('generated_at', 'n/a')} UTC")

st.subheader("What do you want to do?")
a, b, d = st.columns(3)
with a:
    st.markdown('<div class="gl-card"><b>💬 Ask</b><br>Ask questions across the approved and rejected libraries. '
                'Every answer shows its evidence.</div>', unsafe_allow_html=True)
    st.page_link("views/ask.py", label="Open Ask", icon="💬")
with b:
    st.markdown('<div class="gl-card"><b>🩺 Diagnose</b><br>Paste or upload your own proposal and get a rejection-risk score '
                'with ordered fixes.</div>', unsafe_allow_html=True)
    st.page_link("views/diagnose.py", label="Open Diagnose", icon="🩺")
with d:
    st.markdown('<div class="gl-card"><b>📈 Trends & gaps</b><br>See funding trends, under-explored fields and '
                'follow-up opportunities.</div>', unsafe_allow_html=True)
    st.page_link("views/trends.py", label="Open Trends", icon="📈")
