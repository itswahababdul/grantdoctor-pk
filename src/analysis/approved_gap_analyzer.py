"""Spark analysis of the APPROVED library: what is common, what is under-explored, what can be extended."""
from pyspark.sql import DataFrame, Window, functions as F

STOP = ["the", "and", "of", "to", "in", "a", "for", "with", "on", "is", "by", "will", "this", "that", "from", "as", "are", "be", "an", "at", "using", "study"]


def field_profile(df: DataFrame) -> DataFrame:
    return (df.groupBy("field")
            .agg(F.countDistinct("project_id").alias("n_projects"),
                 F.expr("percentile_approx(budget, 0.5)").alias("median_budget"),
                 F.avg("duration_months").alias("avg_duration_months"))
            .orderBy(F.desc("n_projects")))


def underfunded_fields(df: DataFrame, quantile: float = 0.25) -> DataFrame:
    prof = field_profile(df)
    thr = prof.approxQuantile("n_projects", [quantile], 0.01)[0]
    return prof.filter(F.col("n_projects") <= thr)


def top_terms_by_field(df: DataFrame, n: int = 8) -> DataFrame:
    words = (df.select("field", F.explode(F.split(F.lower(F.regexp_replace("abstract", r"[^A-Za-z ]", " ")), r"\s+")).alias("term"))
             .filter((F.length("term") > 3) & (~F.col("term").isin(STOP))))
    counts = words.groupBy("field", "term").count()
    w = Window.partitionBy("field").orderBy(F.desc("count"))
    return counts.withColumn("rank", F.row_number().over(w)).filter(F.col("rank") <= n)


def extension_candidates(df: DataFrame) -> DataFrame:
    """Approved projects described as pilot/preliminary/proof-of-concept = natural scale-up follow-ups."""
    pat = r"(?i)pilot|preliminary|proof[- ]of[- ]concept|initial phase|small[- ]scale"
    return (df.filter(F.col("methodology").rlike(pat) | F.col("abstract").rlike(pat))
            .select("project_id", "title", "field", "year", F.lit("scale up / next phase / multi-site validation").alias("suggested_extension")))


def ref_stats(df: DataFrame) -> dict:
    rows = field_profile(df).collect()
    return {"median_budget_by_field": {r["field"]: r["median_budget"] for r in rows if r["median_budget"]}}
