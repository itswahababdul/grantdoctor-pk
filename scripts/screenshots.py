"""Screenshot every page in light and dark mode (desktop and mobile) into docs/screenshots/.

    python -m playwright install chromium     # once
    python scripts/screenshots.py [--port 8599] [--out docs/screenshots]

Starts the app itself (libraries must be built: `python -m src.app.cli sample && python -m src.app.cli build`).
Streamlit follows the browser's colour scheme, so dark mode is just `color_scheme="dark"`.
"""
import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = [("home", ""), ("ask", "ask"), ("explorer", "explorer"), ("diagnose", "diagnose"), ("rules", "rules"),
         ("trends", "trends"), ("reasons", "reasons"), ("evaluation", "evaluation"), ("about", "about")]
TABS = ["Funding over time", "Fields", "Under-explored", "Extension ideas"]
VIEWPORTS = {"desktop": (1280, 900), "mobile": (390, 844)}


def _wait_ready(pg):
    pg.wait_for_selector('[data-testid="stApp"]', timeout=30000)
    pg.wait_for_selector(".gl-page", timeout=30000)
    pg.wait_for_function("() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=60000)
    time.sleep(2.2)  # plotly + fonts


def _shoot(pg, path: Path):
    """Streamlit scrolls an inner container, so grow the viewport to the content height instead of using full_page."""
    h = pg.evaluate("() => { const m = document.querySelector('[data-testid=\"stMain\"]') || document.documentElement;"
                    " return Math.max(m.scrollHeight, document.documentElement.scrollHeight); }")
    w = pg.viewport_size["width"]
    pg.set_viewport_size({"width": w, "height": min(int(h) + 40, 6000)})
    time.sleep(0.8)
    pg.screenshot(path=str(path))
    pg.set_viewport_size({"width": w, "height": VIEWPORT_H[0]})


VIEWPORT_H = [900]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8599)
    ap.add_argument("--out", default=str(ROOT / "docs/screenshots"))
    a = ap.parse_args()
    out = Path(a.out)
    srv = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "src/app/streamlit_app.py"), "--server.headless", "true",
                            "--server.port", str(a.port), "--browser.gatherUsageStats", "false"],
                           cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    base = f"http://localhost:{a.port}"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/_stcore/health", timeout=2)
                break
            except Exception:
                time.sleep(1)
        with sync_playwright() as p:
            br = p.chromium.launch()
            for vp_name, (w, h) in VIEWPORTS.items():
                VIEWPORT_H[0] = h
                for scheme in ("light", "dark"):
                    ctx = br.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
                    pg = ctx.new_page()
                    d = out / ("mobile" if vp_name == "mobile" else "")
                    d.mkdir(parents=True, exist_ok=True)
                    for name, path in PAGES:
                        pg.goto(f"{base}/{path}")
                        _wait_ready(pg)
                        if name == "trends":
                            for i, tab in enumerate(TABS):
                                pg.get_by_role("tab", name=tab).click()
                                time.sleep(1.6)
                                _shoot(pg, d / f"trends-{i + 1}-{tab.lower().replace(' ', '-')}-{scheme}.png")
                            continue
                        if name == "ask":
                            _shoot(pg, d / f"ask-{scheme}.png")
                            pg.get_by_role("button", name="What funded work exists on groundwater?").click()
                            pg.wait_for_selector("text=Grounding score", timeout=60000)
                            time.sleep(1.5)
                            _shoot(pg, d / f"ask-answer-{scheme}.png")
                            continue
                        if name == "diagnose":
                            _shoot(pg, d / f"diagnose-{scheme}.png")
                            pg.get_by_role("button", name="Load example weak proposal").click()
                            time.sleep(1.5)
                            pg.get_by_role("button", name="Diagnose", exact=True).click()
                            pg.wait_for_selector("text=Step 2: Risk factors", timeout=60000)
                            time.sleep(2)
                            _shoot(pg, d / f"diagnose-results-{scheme}.png")
                            continue
                        _shoot(pg, d / f"{name}-{scheme}.png")
                    ctx.close()
            br.close()
    finally:
        srv.terminate()


if __name__ == "__main__":
    main()
