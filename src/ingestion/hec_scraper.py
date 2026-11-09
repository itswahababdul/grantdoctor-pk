"""HEC (Higher Education Commission) funded-project scraper.

NOTE: Page structure must be checked manually. Update CSS selectors in `parse_listing`
after inspecting the real page. Always respect robots.txt and the site's terms.
"""
import json
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "GrantDoctor-PK academic project (contact: your-email)"}


def allowed_by_robots(url: str) -> bool:
    parsed = urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        return False  # be conservative


def fetch_html(url: str, delay: float = 1.5) -> str:
    if not allowed_by_robots(url):
        raise PermissionError(f"robots.txt disallows {url}")
    time.sleep(delay)
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def parse_listing(html: str, source_url: str) -> list[dict]:
    """TODO: adjust selectors to the real HEC page (table rows / cards)."""
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for i, row in enumerate(soup.select("table tr")[1:]):
        cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        if len(cells) < 3:
            continue
        records.append({
            "project_id": f"HEC-{i:05d}",
            "title": cells[0], "pi": cells[1], "institute": cells[2],
            "abstract": cells[3] if len(cells) > 3 else "",
            "funder": "HEC", "status": "approved", "source_url": source_url,
        })
    return records


def save_jsonl(records: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def scrape(url: str, out_path: str) -> int:
    recs = parse_listing(fetch_html(url), url)
    save_jsonl(recs, out_path)
    return len(recs)
