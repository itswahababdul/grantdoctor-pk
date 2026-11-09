# GrantDoctor-PK: Diagnose why research proposals get rejected (RAG over HEC & PSF projects)

A Spark + Python Retrieval-Augmented Generation system with **two separate libraries**:
- **Approved library** (HEC / PSF funded projects): what works, trends, under-explored fields, extension ideas.
- **Rejected library**: why proposals fail, how to improve them, and 10 *hidden risk factors* that are rarely stated in rejections.

## Quick start (5 commands)
```bash
pip install -r requirements.txt          # needs Java 11/17/21 for Spark
python -m src.app.cli sample             # placeholder data (replace with real HEC/PSF data)
python -m src.app.cli build              # Spark: clean -> chunk -> embed -> 2 indexes
python -m src.app.cli ask "which approved projects study solar panel efficiency?"
python -m src.app.cli diagnose proposal.json
```
**Web UI:** `python -m src.app.cli app` (or `streamlit run src/app/streamlit_app.py`). If nothing is built yet, the Home page has a one-click *Load sample data and build* button.

Extra: `python -m src.app.cli trends` (Spark analytics), `python -m src.app.cli eval` (ablation table), `streamlit run src/app/streamlit_app.py`, `pytest -q`.

## Screenshots
`docs/screenshots/` has every page in light and dark mode (`mobile/` is a 390 px wide phone). Regenerate them after any UI change:
```bash
pip install playwright && python -m playwright install chromium
python scripts/screenshots.py            # needs the libraries built; starts the app itself
```

## Real data now included: PeerRead (accepted vs rejected + reviewer text)
```bash
git clone --depth 1 https://github.com/allenai/PeerRead.git
python -m src.app.cli peerread PeerRead/data   # 172 accepted + 255 rejected ICLR-2017 papers with 7k reviews -> data/raw/
python -m src.app.cli hf-iclr                  # (needs internet + `pip install datasets`) HF rejected ICLR papers with code
python -m src.app.cli build && python -m src.app.cli reasons
```
- These are **conference papers, not grants** (`corpus = peer_review`). They are the only public source where the decision *and* the written reasons are known, so they feed the rejected library (reviews are chunked and searchable) and the **rejection-reason analysis** (`src/analysis/review_reason_miner.py`, page *Why rejected*).
- The analysis compares how often each reason is raised for rejected vs accepted papers (lift, two-proportion z-test, Bonferroni flag), maps each reason to a grant-proposal analogue + fix, and lists reasons **none of the 10 hidden factors checks yet** (candidate "hidden" rejection causes).
- Grant analytics (funding, fields, gaps) use only HEC/PSF-style records; paper data never mixes into them.
- `hf-iclr` could not be run where this was written (huggingface.co unreachable); check the printed column names on first run and adjust `CANDIDATES` in `hf_iclr_loader.py` if needed.
- **Real PSF data is now in:** 57 completed Research Support Programme projects parsed from PSF's public PDF (`python -m src.app.cli psf-pdf <pdf>`). Title-level only: the PDF has no year, budget, PI or abstract.
- **HEC portal (research.hec.gov.pk) has public approved AND rejected lists** (3,418 rejected NRPU projects in YEAR 2020 alone). `scripts/hec_console_download.js` (paste in the browser console on that site) or `scripts/fetch_hec_portal.py` downloads them; the parser is finished once a real record's keys are seen.
- Questions are routed to the grant corpus (HEC/PSF) or the paper corpus (PeerRead) automatically.
- **Still missing: real HEC approved-project data and HEC's rejected list in this build.** The scrapers need selector tuning on the live pages (not reachable when this was built); until real records are in `data/raw/`, grant pages run on the fictional sample.

## Architecture
```
HEC/PSF/ORIC -> ingestion -> [Spark] clean/lang/metadata -> chunk -> embed (mapInPandas)
   -> approved index | rejected index -> hybrid (BM25+dense, RRF) -> rerank -> LLM + guardrails
   -> analyzers (gap, trends, rejection diagnosis, hidden factors, suggestions) -> CLI / Streamlit
```

## Backend and UX structure
```
Streamlit pages (src/app/views)   Home · Ask · Library explorer · Diagnose · Trends & gaps · Evaluation · Data & ethics
        |  (pages hold no business logic)
Services (src/services)           runtime (cached indexes) · qa · library · diagnosis · analytics · eval
        |
Core modules                      retrieval · generation · analysis · vectorstore · evaluation
        |
Spark build step (pipeline.py)    writes Parquet + indexes + analytics CSV/JSON; the UI never starts Spark
```
UX rules: honest data banners (sample / synthetic-rejected), evidence shown under every answer, input validation with clear errors, graceful fallback if the LLM is down, downloadable diagnosis report.

## Official HEC rules
`config/hec_rules.yaml` holds 38 rules read from official HEC NRPU documents (2026-27 FAQs, 2024 policy paper, call SOPs, eligibility page), each with its source link. `src/analysis/hec_rules_checker.py` checks a proposal against them and returns PASS / FAIL / UNKNOWN / IMPROVE per rule. Hard rules (24-month limit, PKR 20M cap, PI eligibility, 19% similarity, 25% AI content, domain, industry for product projects, ORIC endorsement) are checked first; missing inputs are reported as UNKNOWN, never guessed. Rules change per call: re-verify before use. HEC's internal scoring weights are not public, and PSF rules are not included yet.

## Where Spark is used
Ingestion/cleaning/dedup (`cleaner.py`), UDF language + metadata extraction, chunking (explode), distributed embedding (`mapInPandas`), trend analytics, gap analysis, benchmark vs pandas. Outputs are Parquet.

## Modules (one file each)
`ingestion/` scrapers, pdf parser, rejected loader · `preprocessing/` spark session, cleaner, language, metadata, chunker · `embeddings/` · `vectorstore/` · `retrieval/` · `generation/` · `analysis/` · `evaluation/` · `app/` · `tests/`.

## Data & ethics (important)
- Approved projects: public listings only; scrapers check `robots.txt` and need selector adjustment after inspecting the real pages.
- **Rejected proposals are not public.** Use (1) anonymized proposals shared with permission, and/or (2) `synthetic_rejected` records created by controlled degradation (labelled in the `status` and `degradation` columns). The report must state which was used.
- `data/sample/` is fictional placeholder data. Metrics on it are perfect because the data is trivially easy; real data will be harder and numbers will drop. Report real numbers.
- Hidden-factor scores are rule-based heuristics (explainable), not a predictor of actual HEC/PSF decisions.

## Swap-in upgrades
Set `embedding.model` to `intfloat/multilingual-e5-small` or `BAAI/bge-m3` (needs `sentence-transformers`); set `llm.provider: ollama`; replace `base_index.py` with FAISS/Chroma.
