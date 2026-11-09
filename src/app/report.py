"""Printable, self-contained HTML report for one diagnosis. No Streamlit, no external assets.

Every dynamic value is escaped with html.escape. The page prints cleanly (Ctrl/Cmd+P, "Save as PDF").
"""
import datetime as _dt
import html

from src.app.ui import LEVEL_COLOR

DISCLAIMER = ("This report is a heuristic aid, not a decision. The HEC rule check reads the rules listed in the "
              "source documents and uses keyword matching for content rules; the risk score comes from ten explainable "
              "factors. It does not predict the real HEC or PSF decision. Always re-check the current call document "
              "and your full proposal template before submitting.")


def level_of(risk: float) -> str:
    """Same bands the diagnosis service uses for the overall score."""
    return "Low" if risk < 0.35 else "Moderate" if risk < 0.55 else "High"


def _e(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def _name(factor: str) -> str:
    return factor.replace("_", " ").title()


CSS = """
body{font:14px/1.55 -apple-system,"Segoe UI",Inter,Arial,sans-serif;color:#17181b;background:#fff;max-width:820px;margin:2rem auto;padding:0 1.2rem;}
h1{font-size:1.55rem;margin:0 0 .15rem 0;letter-spacing:-.01em;} h2{font-size:1.1rem;margin:1.6rem 0 .5rem 0;border-bottom:1px solid #e3e5e8;padding-bottom:.25rem;}
.sub{color:#555;margin:0 0 1rem 0;} .meta{color:#666;font-size:.85rem;}
.summary{display:flex;gap:1.2rem;align-items:center;border:1px solid #e3e5e8;border-radius:10px;padding:1rem 1.2rem;margin:1rem 0;}
.score{font-size:2.6rem;font-weight:700;line-height:1;} .pill{display:inline-block;color:#fff;border-radius:999px;padding:2px 12px;font-weight:600;font-size:.82rem;}
.card{border:1px solid #e3e5e8;border-left:4px solid #6b7280;border-radius:6px;padding:.6rem .9rem;margin:.5rem 0;break-inside:avoid;}
.card.bad{border-left-color:#b4233c;} .card.warn{border-left-color:#c27a0c;} .card b.fix{color:#0e6b61;}
table{border-collapse:collapse;width:100%;font-size:.9rem;} th,td{text-align:left;border-bottom:1px solid #e3e5e8;padding:.35rem .5rem;} th{color:#555;font-weight:600;}
.disclaimer{margin-top:2rem;border:1px dashed #9ca3af;border-radius:8px;padding:.7rem .9rem;color:#444;font-size:.85rem;}
@media print{body{margin:0;max-width:none;} .summary,.card{break-inside:avoid;} a{color:inherit;text-decoration:none;}}
"""


def build_html(rep: dict, generated_on: str | None = None) -> str:
    p = rep.get("proposal") or {}
    title = p.get("title") or "Untitled proposal"
    date = generated_on or rep.get("generated_on") or _dt.date.today().isoformat()
    risk = float(rep["overall_risk"])
    level = rep.get("level") or level_of(risk)
    hec = rep["hec"]
    n_hard = len(hec["hard_failures"])

    if n_hard:
        verdict = f"{n_hard} hard HEC rule(s) failed. HEC checks eligibility first, so fix these before anything else."
    elif hec["hard_unknown"]:
        verdict = f"No hard rule failed, but {len(hec['hard_unknown'])} could not be checked because inputs are missing."
    else:
        verdict = "All hard HEC rules pass."

    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>GrantDoctor-PK report: {_e(title)}</title><style>{CSS}</style></head><body>",
        "<h1>GrantDoctor-PK diagnosis report</h1>",
        f'<p class="sub">{_e(title)}</p>',
        f'<p class="meta">Generated {_e(date)} · HEC rules read from HEC documents on {_e(hec.get("verified_on"))}</p>',
        '<div class="summary">',
        f'<div><div class="score">{risk:.2f}</div><div class="meta">overall rejection risk (0 to 1)</div></div>',
        f'<div><span class="pill" style="background:{LEVEL_COLOR.get(level, "#6b7280")}">{_e(level)} risk</span>',
        f'<div>{_e(verdict)}</div>',
        f'<div class="meta">HEC rules: {hec["n_pass"]} pass · {hec["n_fail"]} fail · {hec["n_unknown"]} need input · {hec["n_improve"]} to improve</div></div>',
        "</div>",
        "<h2>Hard failures</h2>",
    ]
    if hec["hard_failures"]:
        for x in hec["hard_failures"]:
            out.append(f'<div class="card bad"><b>{_e(x["id"])} · {_e(x["title"])}</b><br>{_e(x["detail"])}'
                       f'<br><b class="fix">Fix:</b> {_e(x["fix"])}<br><span class="meta">Source: {_e(x["source"])}</span></div>')
    else:
        out.append("<p>None.</p>")
    if hec["hard_unknown"]:
        out.append("<h2>Not checked yet (inputs missing)</h2><ul>")
        out += [f'<li><b>{_e(x["id"])}</b> {_e(x["title"])}: {_e(x["detail"])}</li>' for x in hec["hard_unknown"]]
        out.append("</ul>")

    out.append("<h2>Fix these first</h2>")
    for i, s in enumerate(rep.get("suggestions") or [], 1):
        lvl = level_of(s["risk"])
        out.append(f'<div class="card {"bad" if lvl == "High" else "warn" if lvl == "Moderate" else ""}">'
                   f'<b>{i}. {_e(_name(s["factor"]))}</b> <span class="meta">(risk {s["risk"]:.2f}, {lvl})</span>'
                   f'<br>Why: {_e(s["why"])}<br><b class="fix">Fix:</b> {_e(s["fix"])}</div>')

    out.append("<h2>All risk factors</h2><table><tr><th>Factor</th><th>Risk</th><th>Level</th><th>Note</th></tr>")
    for k, v in sorted(rep["factors"].items(), key=lambda kv: -kv[1]["risk"]):
        out.append(f'<tr><td>{_e(_name(k))}</td><td>{v["risk"]:.2f}</td><td>{level_of(v["risk"])}</td><td>{_e(v["note"])}</td></tr>')
    out.append("</table>")
    out.append(f'<div class="disclaimer"><b>Disclaimer.</b> {_e(DISCLAIMER)}</div></body></html>')
    return "".join(out)
