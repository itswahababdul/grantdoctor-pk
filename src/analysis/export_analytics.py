"""Run the Spark analytics once at build time and save small CSV/JSON files.
The UI reads these files, so the web app never has to start Spark."""
import json
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import SparkSession, functions as F

from src.analysis import approved_gap_analyzer as gap
from src.analysis import trend_analytics_spark as trend


def export_all(spark: SparkSession, processed_dir: Path) -> dict:
    processed_dir = Path(processed_dir)
    out_dir = processed_dir / "analytics"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_df = spark.read.parquet(str(processed_dir / "projects.parquet"))
    # grant analytics use HEC/PSF-style records only; paper-review data is analysed separately (review_reason_miner)
    df = all_df.filter(F.col("corpus").isNull() | (F.col("corpus") != "peer_review"))
    approved = df.filter(F.col("status") == "approved")

    tables = {
        "funding_by_year_funder": trend.funding_by_year_funder(df),
        "approval_rate_by_field": trend.approval_rate_by_field(df),
        "field_profile": gap.field_profile(approved),
        "underfunded_fields": gap.underfunded_fields(approved),
        "top_terms_by_field": gap.top_terms_by_field(approved),
        "extension_candidates": gap.extension_candidates(approved),
    }
    for name, sdf in tables.items():
        sdf.toPandas().to_csv(out_dir / f"{name}.csv", index=False)

    counts = {r["status"]: r["count"] for r in df.groupBy("status").count().collect()}
    pr = all_df.filter(F.col("corpus") == "peer_review")
    pr_counts = {r["status"]: r["count"] for r in pr.groupBy("status").count().collect()}
    reasons = _export_reasons(pr, out_dir)
    ids = [r["project_id"] for r in df.select("project_id").limit(50).collect()]
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_projects": df.count(),
        "n_approved": counts.get("approved", 0),
        "n_rejected_real": counts.get("rejected", 0),
        "n_rejected_synthetic": counts.get("synthetic_rejected", 0),
        "funders": sorted(r["funder"] for r in df.select("funder").distinct().collect() if r["funder"]),
        "n_fields": df.select("field").distinct().count(),
        "n_peer_review_accepted": pr_counts.get("approved", 0),
        "n_peer_review_rejected": pr_counts.get("rejected", 0),
        "n_reason_papers": reasons,
        "is_sample_data": any(i.startswith("SAMPLE-") for i in ids),
    }
    with open(out_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    return meta


def _export_reasons(pr, out_dir: Path) -> int:
    """Rejection-reason analysis on reviewer text (pandas; the data is small). Returns #papers with reviews."""
    from src.analysis.review_reason_miner import mine_reasons
    if pr.count() == 0:
        return 0
    pdf = pr.select("project_id", "status", "review_text", "meta_review").toPandas()
    tbl = mine_reasons(pdf)
    tbl.to_csv(out_dir / "rejection_reasons.csv", index=False)
    return int((pdf["review_text"].fillna("").str.len() > 40).sum())
