"""Shared UI: design system (CSS variables, components) + build panel + honest-data banners.

No business logic here: that lives in src/services. Every component HTML-escapes the text it is given.
Colours adapt to light/dark because surfaces and borders are mixed from `currentColor`
(the active Streamlit theme's text colour) instead of fixed backgrounds.
"""
import html
import re
import subprocess
import sys

import streamlit as st

from src.config import ROOT
from src.services import analytics_service, runtime
from src.services.display_service import fmt_pkr  # noqa: F401  (re-exported for pages)

# ----------------------------------------------------------------------------- design tokens
LEVEL_COLOR = {"Low": "#0e8a7d", "Moderate": "#c27a0c", "High": "#b4233c"}
TONES = {"neutral": "var(--gl-neutral)", "success": "var(--gl-ok)", "teal": "var(--gl-accent)",
         "warning": "var(--gl-warn)", "danger": "var(--gl-bad)", "info": "var(--gl-info)"}
CALLOUT_KINDS = {"info": "info", "success": "success", "warning": "warning", "error": "danger", "note": "neutral"}
PALETTE = ["#0e8a7d", "#3b6fb6", "#c27a0c", "#b4233c", "#7a5bb5", "#6b7280"]  # chart colours: the theme tokens first

CSS = """
<style class="gl-css">
:root{
  --gl-accent:#0e8a7d; --gl-ok:#0e8a7d; --gl-warn:#c27a0c; --gl-bad:#b4233c; --gl-info:#3b6fb6; --gl-neutral:#6b7280;
  --gl-radius:14px; --gl-radius-sm:10px;
  --gl-border:color-mix(in srgb, currentColor 14%, transparent);
  --gl-surface:color-mix(in srgb, currentColor 4%, transparent);
  --gl-surface-2:color-mix(in srgb, currentColor 7%, transparent);
  --gl-shadow:0 8px 24px color-mix(in srgb, currentColor 11%, transparent);
}
/* chrome: hide deploy button, main menu, footer; keep the (transparent) header so the sidebar toggle still works */
#MainMenu, footer, [data-testid="stMainMenu"], [data-testid="stAppDeployButton"], .stDeployButton,
[data-testid="stToolbarActions"], [data-testid="stDecoration"]{display:none !important;}
[data-testid="stHeader"], header[data-testid="stHeader"]{background:transparent !important;}
/* the element that holds this stylesheet should take no space */
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdownContainer"] > style.gl-css),
.element-container:has(> [data-testid="stMarkdownContainer"] > style.gl-css){display:none;}
/* spacing */
.block-container{padding-top:2.2rem !important; padding-bottom:3rem !important; max-width:1180px;}
[data-testid="stVerticalBlock"]{gap:0.85rem;}
/* page header */
.gl-page{margin:0 0 0.4rem 0;}
.gl-page h1{font-size:1.9rem; font-weight:650; letter-spacing:-0.02em; line-height:1.2; margin:0; padding:0;}
.gl-page p{margin:0.35rem 0 0 0; opacity:0.68; font-size:0.97rem;}
/* hero */
.gl-hero{border:1px solid var(--gl-border); border-radius:calc(var(--gl-radius) + 4px); padding:2rem 2.1rem;
  background:linear-gradient(135deg, color-mix(in srgb, var(--gl-accent) 20%, transparent), transparent 68%), var(--gl-surface);}
.gl-hero .gl-eyebrow{font-size:0.75rem; font-weight:600; letter-spacing:0.09em; text-transform:uppercase; color:var(--gl-accent);}
.gl-hero h1{font-size:2.4rem; font-weight:700; letter-spacing:-0.03em; line-height:1.1; margin:0.35rem 0 0.6rem 0; padding:0;}
.gl-hero p{margin:0; max-width:46rem; opacity:0.78; font-size:1.02rem; line-height:1.55;}
/* cards */
.gl-card, .gl-kpi, .gl-evidence, .gl-empty, .gl-callout{border:1px solid var(--gl-border); border-radius:var(--gl-radius); background:var(--gl-surface);}
.gl-card{padding:1rem 1.2rem; height:100%; line-height:1.5;}
.gl-card, .gl-kpi{transition:box-shadow .18s ease, transform .18s ease, border-color .18s ease;}
.gl-card:hover, .gl-kpi:hover{box-shadow:var(--gl-shadow); transform:translateY(-1px); border-color:color-mix(in srgb, var(--gl-accent) 45%, transparent);}
.gl-kpi{padding:1rem 1.2rem;}
.gl-kpi .gl-label{font-size:0.78rem; font-weight:600; letter-spacing:0.05em; text-transform:uppercase; opacity:0.62;}
.gl-kpi .gl-value{font-size:2rem; font-weight:650; letter-spacing:-0.02em; line-height:1.15; margin-top:0.25rem;}
.gl-kpi .gl-hint{font-size:0.82rem; opacity:0.62; margin-top:0.2rem;}
/* native metrics look like KPI cards too */
[data-testid="stMetric"]{border:1px solid var(--gl-border); border-radius:var(--gl-radius); background:var(--gl-surface); padding:0.85rem 1.1rem;}
/* badges */
.gl-badge{display:inline-block; padding:2px 11px; border-radius:999px; color:#fff; font-weight:600; font-size:0.8rem; line-height:1.5; letter-spacing:0.01em;}
/* evidence */
.gl-evidence{border-left:4px solid var(--gl-neutral); border-radius:4px var(--gl-radius-sm) var(--gl-radius-sm) 4px; padding:0.65rem 0.95rem; margin:0.45rem 0; line-height:1.5;}
.gl-evidence .gl-meta{font-size:0.8rem; opacity:0.66; margin:0.1rem 0 0.35rem 0;}
.gl-approved{border-left-color:var(--gl-ok);} .gl-rejected{border-left-color:var(--gl-bad);}
/* section */
.gl-section{margin:1.1rem 0 0.2rem 0;}
.gl-section h3{font-size:1.15rem; font-weight:620; letter-spacing:-0.01em; margin:0; padding:0;}
.gl-section p{margin:0.15rem 0 0 0; opacity:0.64; font-size:0.9rem;}
/* empty state */
.gl-empty{border-style:dashed; padding:1.6rem 1.4rem; text-align:center;}
.gl-empty b{display:block; font-size:1.02rem; margin-bottom:0.25rem;} .gl-empty span{opacity:0.66; font-size:0.92rem;}
/* callout */
.gl-callout{border-left:4px solid var(--gl-neutral); padding:0.7rem 1rem; line-height:1.5; font-size:0.94rem;
  background:color-mix(in srgb, var(--gl-tone, var(--gl-neutral)) 9%, transparent);}
.gl-callout{border-left-color:var(--gl-tone, var(--gl-neutral));}
.gl-tone-info{--gl-tone:var(--gl-info);} .gl-tone-success{--gl-tone:var(--gl-ok);}
.gl-tone-warning{--gl-tone:var(--gl-warn);} .gl-tone-danger{--gl-tone:var(--gl-bad);} .gl-tone-neutral{--gl-tone:var(--gl-neutral);}
/* long text never pushes a card wider than the screen */
.gl-card, .gl-evidence, .gl-callout, .gl-kpi, .gl-fact, .gl-detail-title, .gl-prose{overflow-wrap:anywhere; min-width:0;}
.gl-evidence img, .gl-card img{max-width:100%;}
/* card grids, chips, detail panels */
.gl-grid{display:grid; grid-template-columns:repeat(auto-fill, minmax(250px, 1fr)); gap:0.85rem;}
.gl-grid .gl-card{display:flex; flex-direction:column; gap:0.3rem;}
.gl-card-head{display:flex; flex-wrap:wrap; align-items:center; gap:0.25rem 0.55rem; line-height:1.4;}
.gl-card-title{font-weight:620; font-size:1rem; letter-spacing:-0.005em;}
.gl-card-body{font-size:0.92rem; opacity:0.82;} .gl-card-meta{font-size:0.8rem; opacity:0.62;}
.gl-card-meta a, .gl-fact a{text-decoration:none;} .gl-card-meta a:hover, .gl-fact a:hover{text-decoration:underline;}
.gl-tonebar{background:linear-gradient(var(--gl-tone, var(--gl-neutral)), var(--gl-tone, var(--gl-neutral))) top/100% 3px no-repeat, var(--gl-surface);}
.gl-grid{margin:0.6rem 0 0.5rem 0;}
.gl-detail-head{margin-bottom:0.9rem;}
.gl-src-title{min-height:2.8em; font-weight:620; line-height:1.4;}
/* links: teal that stays readable on both themes */
.gl-card-meta a, .gl-fact a, .gl-evidence.gl-rule a{color:color-mix(in srgb, var(--gl-accent) 65%, currentColor);}
/* the dataframe hover toolbar floats above the table: keep it clear of the row above */
[data-testid="stDataFrame"]{margin-top:0.7rem;}
/* long example questions wrap instead of being cut off */
[class*="st-key-ask_ex_"] button{white-space:normal; height:auto; min-height:2.6rem; padding:0.5rem 0.9rem;}
[class*="st-key-ask_ex_"] button p{white-space:normal; text-align:left;}
.gl-toned{border-left-color:var(--gl-tone, var(--gl-neutral));}
.gl-tone-teal{--gl-tone:var(--gl-accent);}
.gl-chip{display:inline-flex; align-items:center; gap:0.4rem; border:1px solid var(--gl-border); border-radius:999px; background:var(--gl-surface);
  padding:0.25rem 0.9rem; font-size:0.88rem; font-weight:550;}
.gl-chip b{color:var(--gl-accent); font-weight:700;}
.gl-detail-title{font-size:1.3rem; font-weight:650; letter-spacing:-0.01em; line-height:1.3; margin:0 0 0.35rem 0;}
.gl-prose{margin:0 0 0.9rem 0; line-height:1.55;} .gl-prose h4{font-size:0.78rem; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; opacity:0.62; margin:0 0 0.2rem 0; padding:0;}
.gl-fact{border:1px solid var(--gl-border); border-radius:var(--gl-radius-sm); background:var(--gl-surface); padding:0.2rem 1rem;}
.gl-fact-row{padding:0.55rem 0; border-bottom:1px solid var(--gl-border); line-height:1.4;} .gl-fact-row:last-child{border-bottom:none;}
.gl-fact-k{font-size:0.74rem; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; opacity:0.6;}
.gl-fact-v{font-weight:550; overflow-wrap:anywhere;}
/* native widgets */
[data-testid="stAlert"], [data-testid="stExpander"], [data-testid="stDataFrame"], [data-testid="stForm"]{border-radius:var(--gl-radius-sm) !important;}
[data-testid="stForm"], [data-testid="stExpander"]{border-color:var(--gl-border) !important;}
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button{border-radius:var(--gl-radius-sm); font-weight:550; transition:box-shadow .15s ease;}
.stButton > button:hover, .stDownloadButton > button:hover{box-shadow:var(--gl-shadow);}
[data-testid="stTabs"] [role="tab"]{font-weight:550;}
</style>
"""


# ----------------------------------------------------------------------------- helpers
def esc(x) -> str:
    """Escape for safe use inside st.markdown(unsafe_allow_html=True): HTML, markdown and $math characters."""
    s = html.escape("" if x is None else str(x), quote=True)
    for ch, ent in (("*", "&#42;"), ("_", "&#95;"), ("`", "&#96;"), ("~", "&#126;"), ("$", "&#36;"),
                    ("[", "&#91;"), ("]", "&#93;"), ("\\", "&#92;")):
        s = s.replace(ch, ent)
    return s.replace("\r\n", "\n").replace("\n", "<br>")


def _render(markup: str):
    st.markdown(markup.replace("\n", ""), unsafe_allow_html=True)  # no blank lines: keeps it one HTML block


def _tone_color(tone: str) -> str:
    if tone in TONES:
        return TONES[tone]
    if isinstance(tone, str) and re.fullmatch(r"#[0-9a-fA-F]{3,8}", tone):  # legacy callers pass a hex colour
        return tone
    return TONES["neutral"]


def inject_css():
    """Inject the stylesheet once per script run (page_header calls it; the entry point calls it too).

    Streamlit gives every run a fresh `cursors` dict on the script-run context, so holding a reference to it
    in session_state tells us whether this run already injected the CSS.
    """
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        run_marker = getattr(get_script_run_ctx(suppress_warning=True), "cursors", None)
    except Exception:
        run_marker = None
    if run_marker is not None:
        if st.session_state.get("_gl_css_run") is run_marker:
            return
        st.session_state["_gl_css_run"] = run_marker
    st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------- components
def page_header(title: str, subtitle: str = ""):
    inject_css()
    sub = f"<p>{esc(subtitle)}</p>" if subtitle else ""
    _render(f'<div class="gl-page"><h1>{esc(title)}</h1>{sub}</div>')


def hero(title: str = "GrantDoctor-PK", text: str = "", eyebrow: str = ""):
    inject_css()
    eb = f'<div class="gl-eyebrow">{esc(eyebrow)}</div>' if eyebrow else ""
    body = f"<p>{esc(text)}</p>" if text else ""
    _render(f'<div class="gl-hero">{eb}<h1>{esc(title)}</h1>{body}</div>')


def kpi_card(label: str, value, hint: str = ""):
    inject_css()
    h = f'<div class="gl-hint">{esc(hint)}</div>' if hint else ""
    _render(f'<div class="gl-kpi"><div class="gl-label">{esc(label)}</div><div class="gl-value">{esc(value)}</div>{h}</div>')


def badge(text: str, tone: str = "neutral") -> str:
    """Returns an HTML string (render with st.markdown(..., unsafe_allow_html=True)). `tone` is a name or a #hex colour."""
    return f'<span class="gl-badge" style="background:{_tone_color(tone)}">{esc(text)}</span>'


badge_html = badge


def evidence_card(project_id, title=None, text="", library=None, field=None, funder=None, year=None,
                  section=None, score=None, degradation=None):
    inject_css()
    cls = {"approved": " gl-approved", "rejected": " gl-rejected"}.get(str(library), "")
    meta = " · ".join(esc(x) for x in (library, field, funder, year) if x)
    if degradation:
        meta += f" · degradation: {esc(degradation)}"
    if section:
        meta += f" · section: {esc(section)}"
    if score is not None:
        meta += f" · score {esc(score)}"
    head = f"<b>[{esc(project_id)}]</b> {esc(title)}" if title else f"<b>[{esc(project_id)}]</b>"
    _render(f'<div class="gl-evidence{cls}">{head}<div class="gl-meta">{meta}</div><div>{esc(text)}</div></div>')


def section(title: str, caption: str = ""):
    inject_css()
    cap = f"<p>{esc(caption)}</p>" if caption else ""
    _render(f'<div class="gl-section"><h3>{esc(title)}</h3>{cap}</div>')


def empty_state(title: str, text: str = ""):
    inject_css()
    body = f"<span>{esc(text)}</span>" if text else ""
    _render(f'<div class="gl-empty"><b>{esc(title)}</b>{body}</div>')


def callout(kind: str, text: str):
    """kind: info | success | warning | error | note"""
    inject_css()
    tone = CALLOUT_KINDS.get(kind, "neutral")
    _render(f'<div class="gl-callout gl-tone-{tone}">{esc(text)}</div>')


def chip(value, label: str = "") -> str:
    """Small rounded count chip as an HTML string, e.g. chip(42, 'projects')."""
    lab = f"<span>{esc(label)}</span>" if label else ""
    return f'<span class="gl-chip"><b>{esc(value)}</b>{lab}</span>'


def card(title: str, body=(), *, badge: tuple | None = None, tone: str | None = None, meta: str = "") -> str:
    """Card as an HTML string. `body` is a string or a list of paragraphs, `badge` is (text, tone). All text is escaped."""
    paras = [body] if isinstance(body, str) else list(body)
    inner = "".join(f'<div class="gl-card-body">{esc(p)}</div>' for p in paras if p)
    b = badge_html(*badge) if badge else ""
    cls = f" gl-tonebar gl-tone-{tone}" if tone else ""
    m = f'<div class="gl-card-meta">{esc(meta)}</div>' if meta else ""
    return (f'<div class="gl-card{cls}"><div class="gl-card-head"><span class="gl-card-title">{esc(title)}</span>{b}</div>'
            f'{inner}{m}</div>')


def grid(cards: list[str]):
    """Render cards (from card()) as a responsive grid."""
    inject_css()
    _render(f'<div class="gl-grid">{"".join(cards)}</div>')


def funder_colors(names) -> dict:
    """Stable colour per funder: HEC teal, PSF blue, any other funder from the rest of the palette."""
    fixed = {"HEC": PALETTE[0], "PSF": PALETTE[1]}
    spare = [c for c in PALETTE if c not in fixed.values()]
    out, i = {}, 0
    for n in names:
        if n in fixed:
            out[n] = fixed[n]
        else:
            out[n] = spare[i % len(spare)]
            i += 1
    return out


def style_fig(fig, title: str = "", height: int = 360, legend: bool = True):
    """One look for every Plotly chart: transparent background, theme colours, left-aligned title, light grid."""
    grid_c = "rgba(128,128,128,0.22)"
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15)) if title else None,
        height=height, margin=dict(l=8, r=12, t=48 if title else 12, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", colorway=PALETTE, showlegend=legend,
        legend=dict(orientation="h", yanchor="top", y=-0.16, xanchor="left", x=0, title_text="", traceorder="normal"),
        hoverlabel=dict(font_size=13), bargap=0.3)
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=grid_c)
    fig.update_yaxes(gridcolor=grid_c, zeroline=False)
    return fig


PLOT_CONFIG = {"displayModeBar": False}


# ----------------------------------------------------------------------------- build panel + honest-data banners
def is_ready() -> bool:
    return runtime.is_built() and analytics_service.available()


def _run_cli(*args: str) -> tuple[bool, str]:
    p = subprocess.run([sys.executable, "-m", "src.app.cli", *args], cwd=str(ROOT), capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr)[-1500:]


def _run_script(path: str) -> tuple[bool, str]:
    p = subprocess.run([sys.executable, path], cwd=str(ROOT), capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr)[-1500:]


def build_panel():
    """Shown on pages when the libraries have not been built yet."""
    inject_css()
    st.warning("The libraries are not built yet.")
    st.write("Click the button to build the libraries from the real HEC data in `data/hec_data.json`.")
    if st.button("Load HEC data and build libraries", type="primary"):
        with st.spinner("Running the Spark pipeline (about a minute the first time)..."):
            ok1, log1 = _run_script("scripts/ingest_hec_data.py")
            ok2, log2 = _run_cli("build") if ok1 else (False, log1)
        if ok2:
            runtime.reset_runtime()
            st.success("Built. Reloading...")
            st.rerun()
        else:
            st.error("Build failed.")
            st.code(log1 + log2)


def require_ready():
    if not is_ready():
        build_panel()
        st.stop()


def data_banner():
    """Honest-data banners. Kept as native st.info / st.warning (same text as before)."""
    m = analytics_service.meta()
    if m.get("is_sample_data"):
        st.info("Demo mode: this is **fictional sample data**. Replace it with real HEC/PSF data before drawing conclusions.")
    if m.get("n_rejected_synthetic", 0) and not m.get("n_rejected_real", 0):
        st.warning("The rejected library contains only **synthetic** rejected proposals (controlled degradation of approved ones), "
                   "not real HEC/PSF rejections. Treat rejection analysis as a method demonstration.")
