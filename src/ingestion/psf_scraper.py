"""Pakistan Science Foundation (PSF) funded-project scraper. Same rules as hec_scraper."""
from src.ingestion.hec_scraper import fetch_html, save_jsonl
from bs4 import BeautifulSoup


def parse_listing(html: str, source_url: str) -> list[dict]:
    """TODO: adjust selectors to the real PSF page."""
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for i, row in enumerate(soup.select("table tr")[1:]):
        cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        if len(cells) < 3:
            continue
        records.append({
            "project_id": f"PSF-{i:05d}",
            "title": cells[0], "pi": cells[1], "institute": cells[2],
            "abstract": cells[3] if len(cells) > 3 else "",
            "funder": "PSF", "status": "approved", "source_url": source_url,
        })
    return records


def scrape(url: str, out_path: str) -> int:
    recs = parse_listing(fetch_html(url), url)
    save_jsonl(recs, out_path)
    return len(recs)
