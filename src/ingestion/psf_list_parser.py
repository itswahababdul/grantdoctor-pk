"""Parse PSF's public 'List of Completed Projects (Last Five Years) under Research Support Programme' PDF.
Each entry = project code like PSF/Res/S-KU/Bio (454) + title. The PDF has NO year, budget, PI or abstract,
so records are title-level only and honestly labelled (status approved = funded and completed).
    python -m src.app.cli psf-pdf rs_list_of_completed_projects_last_five_years.pdf
"""
import json
import re
import subprocess
from pathlib import Path

DISC = {"bio": "Biological Sciences", "med": "Medical Sciences", "chem": "Chemistry", "agr": "Agriculture",
        "comp": "Computer Science", "earth": "Earth Sciences", "engg": "Engineering", "phys": "Physics",
        "biotech": "Biotechnology", "math": "Mathematics", "env": "Environmental Sciences"}
REGION = {"s": "Sindh", "p": "Punjab", "b": "Balochistan", "c": "Capital Territory", "kpk": "Khyber Pakhtunkhwa"}


def parse_text(text: str) -> list[dict]:
    parts = re.split(r"(?m)^\s*(\d{1,3})\.\s+(?=PSF)", text)
    recs = []
    for i in range(1, len(parts), 2):
        sno, body = parts[i], re.sub(r"\s+", " ", parts[i + 1]).strip()
        m = re.match(r"(PSF/.*?)\s*\((\d+)\)\s*(.*)$", body)
        if not m:
            continue
        code, num, title = m.group(1).replace(" ", ""), m.group(2), m.group(3).strip()
        segs = [s for s in code.split("/") if s]
        disc = DISC.get(segs[-1].lower(), segs[-1])
        reg = re.search(r"(?:^|/)(KPK|S|P|B|C)-([A-Za-z0-9.\-]+)", code)
        if len(title) < 10:
            continue
        recs.append({
            "project_id": f"PSF-{num}", "title": title, "abstract": title, "objectives": "", "methodology": "",
            "field": disc, "institute": reg.group(2) if reg else None,
            "province": REGION.get(reg.group(1).lower()) if reg else None,
            "funder": "PSF", "status": "approved", "corpus": "grant", "year": None,
            "source_url": "https://psf.gov.pk/downloads/rs/rs_list_of_completed_projects_last_five_years.pdf",
            "psf_code": code,
        })
    return recs


def write_psf(pdf_path: str, raw_dir: str) -> dict:
    text = subprocess.run(["pdftotext", "-layout", pdf_path, "-"], capture_output=True, text=True, check=True).stdout
    recs = parse_text(text)
    out = Path(raw_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "psf_completed.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs), encoding="utf-8")
    return {"psf_completed": len(recs)}
