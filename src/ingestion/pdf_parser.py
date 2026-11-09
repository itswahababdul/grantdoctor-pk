"""Extract text from proposal/summary PDFs and split into labelled sections."""
import re
from pypdf import PdfReader

SECTION_PATTERNS = {
    "abstract": r"abstract|executive summary",
    "objectives": r"objectives?|aims?",
    "methodology": r"methodology|methods?|research design",
}


def pdf_to_text(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def split_sections(text: str) -> dict:
    """Heuristic heading-based split. Returns {section: text}."""
    heads = []
    for name, pat in SECTION_PATTERNS.items():
        for m in re.finditer(rf"(?im)^\s*(?:\d+[.)]\s*)?({pat})\s*:?\s*$", text):
            heads.append((m.start(), m.end(), name))
    heads.sort()
    out = {k: "" for k in SECTION_PATTERNS}
    for i, (_, end, name) in enumerate(heads):
        nxt = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        out[name] = text[end:nxt].strip()
    if not any(out.values()):
        out["abstract"] = text.strip()
    return out
