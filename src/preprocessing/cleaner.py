"""Spark cleaning: schema enforcement, HTML/whitespace cleanup, type casting, dedup."""
from pyspark.sql import DataFrame, SparkSession, functions as F

from src.config import load_schema

TEXT_COLS = ["title", "abstract", "objectives", "methodology", "review_text", "meta_review"]


def load_raw(spark: SparkSession, *paths: str) -> DataFrame:
    df = None
    for p in paths:
        part = spark.read.json(p)
        df = part if df is None else df.unionByName(part, allowMissingColumns=True)
    return df


def ensure_schema(df: DataFrame) -> DataFrame:
    for c in load_schema()["fields"]:
        if c not in df.columns:
            df = df.withColumn(c, F.lit(None).cast("string"))
    return df


def clean(df: DataFrame, min_abstract_chars: int = 50) -> DataFrame:
    df = ensure_schema(df)
    for c in TEXT_COLS:
        df = df.withColumn(
            c,
            F.trim(F.regexp_replace(F.regexp_replace(F.coalesce(F.col(c).cast("string"), F.lit("")), r"<[^>]+>", " "), r"\s+", " ")),
        )
    # portal lists (HEC/PSF) often have a title but no abstract: use the title as the searchable text instead of dropping the record
    df = df.withColumn("abstract", F.when((F.length("abstract") < min_abstract_chars) & (F.length("title") >= 10), F.col("title")).otherwise(F.col("abstract")))
    df = df.filter(F.length("abstract") >= 10)
    df = df.filter((F.length("abstract") >= min_abstract_chars) | (F.length("title") >= 10))
    df = df.withColumn("budget", F.col("budget").cast("double"))
    df = df.withColumn("duration_months", F.col("duration_months").cast("int"))
    df = df.withColumn("year", F.col("year").cast("int"))
    df = df.withColumn("title_key", F.lower(F.regexp_replace("title", r"[^a-zA-Z0-9]", "")))
    df = df.dropDuplicates(["title_key", "funder", "status", "pi", "year"]).drop("title_key")
    return df
