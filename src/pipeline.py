"""Orchestration: raw -> Spark clean -> chunk -> embed -> two separate indexes + reference stats."""
import json
from pathlib import Path

import pandas as pd

from src.analysis.approved_gap_analyzer import ref_stats
from src.analysis.export_analytics import export_all
from src.config import abs_path, load_config
from src.embeddings.embedder import get_embedder
from src.embeddings.spark_embed_udf import embed_dataframe
from src.ingestion.rejected_loader import make_synthetic_negatives
from src.preprocessing.chunker import chunk_dataframe
from src.preprocessing.cleaner import clean, load_raw
from src.preprocessing.language_detect import add_language
from src.preprocessing.metadata_extractor import fill_metadata
from src.preprocessing.spark_session import get_spark
from src.vectorstore.approved_index import ApprovedIndex
from src.vectorstore.rejected_index import RejectedIndex


def build(source_dir: str | None = None, synthetic_rejected: bool = True, cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    src = Path(abs_path(source_dir or cfg["paths"]["raw_dir"]))
    proc, idx = abs_path(cfg["paths"]["processed_dir"]), abs_path(cfg["paths"]["index_dir"])
    proc.mkdir(parents=True, exist_ok=True)
    spark = get_spark(master=cfg["spark"]["master"], shuffle_partitions=cfg["spark"]["shuffle_partitions"])

    files = [str(p) for p in src.glob("*.jsonl")]
    if not files:
        raise FileNotFoundError(f"No .jsonl files in {src}. Run `python -m src.app.cli sample` or add real data.")

    # synthetic negatives (clearly labelled) if no real rejected file exists
    # (peer-review corpora have their own real rejected papers, so they do not count here)
    grant_files = [f for f in files if not Path(f).name.startswith(("peerread", "hf_"))]
    if synthetic_rejected and grant_files and not any("rejected" in Path(f).name for f in grant_files):
        approved = [json.loads(l) for f in grant_files for l in Path(f).read_text(encoding="utf-8").splitlines() if l.strip()]
        # degradation only makes sense for records that HAVE methodology/objectives (not title-only portal lists)
        base = [a for a in approved if a.get("status") == "approved" and a.get("corpus") != "peer_review" and a.get("methodology")]
        syn = make_synthetic_negatives(base)
        if syn:
            syn_path = proc / "synthetic_rejected.jsonl"
            with open(syn_path, "w", encoding="utf-8") as f:
                for r in syn:
                    f.write(json.dumps(r) + "\n")
            files.append(str(syn_path))

    df = fill_metadata(add_language(clean(load_raw(spark, *files))))
    df.write.mode("overwrite").parquet(str(proc / "projects.parquet"))

    chunks = chunk_dataframe(df, cfg["chunking"]["chunk_words"], cfg["chunking"]["overlap_words"])
    emb = embed_dataframe(chunks, cfg["embedding"]["model"])
    emb.write.mode("overwrite").parquet(str(proc / "chunks_embedded.parquet"))

    pdf = pd.read_parquet(proc / "chunks_embedded.parquet")
    approved_pdf = pdf[pdf["status"] == "approved"].reset_index(drop=True)
    rejected_pdf = pdf[pdf["status"].isin(RejectedIndex.STATUSES)].reset_index(drop=True)
    ApprovedIndex().build_from_pandas(approved_pdf).save(str(idx / "approved"))
    RejectedIndex().build_from_pandas(rejected_pdf).save(str(idx / "rejected"))

    stats = ref_stats(spark.read.parquet(str(proc / "projects.parquet")).filter("status = 'approved' AND (corpus IS NULL OR corpus != 'peer_review')"))
    with open(proc / "ref_stats.json", "w") as f:
        json.dump(stats, f)
    meta = export_all(spark, proc)
    return {"projects": meta["n_projects"], "approved_chunks": len(approved_pdf), "rejected_chunks": len(rejected_pdf)}


def load_runtime(cfg: dict | None = None):
    """Load indexes + retriever for querying (no Spark needed at query time)."""
    from src.retrieval.hybrid_retriever import HybridRetriever
    cfg = cfg or load_config()
    idx = abs_path(cfg["paths"]["index_dir"])
    indexes = {"approved": ApprovedIndex.load(str(idx / "approved")),
               "rejected": RejectedIndex.load(str(idx / "rejected"))}
    embedder = get_embedder(cfg["embedding"]["model"])
    stats_path = abs_path(cfg["paths"]["processed_dir"]) / "ref_stats.json"
    stats = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.exists() else {}
    return HybridRetriever(indexes, embedder), embedder, indexes, stats


def answer(question: str, cfg: dict | None = None) -> dict:
    from src.generation.guardrails import guard
    from src.generation.llm_client import LLMClient
    from src.generation.prompts import build_prompt
    from src.retrieval.query_router import route, route_corpus
    cfg = cfg or load_config()
    retriever, _, _, _ = load_runtime(cfg)
    libs = route(question)
    ctx = retriever.retrieve(question, libs, k=cfg["retrieval"]["top_k"], pool=cfg["retrieval"]["candidate_pool"], corpus=route_corpus(question))
    llm = LLMClient(cfg["llm"]["provider"], cfg["llm"]["model"], cfg["llm"]["url"])
    return {"libraries": libs, "answer": guard(llm.generate(build_prompt(question, ctx), ctx), ctx), "contexts": ctx}
