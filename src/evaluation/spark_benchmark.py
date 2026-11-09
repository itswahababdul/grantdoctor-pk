"""Scalability benchmark: pandas vs Spark on the same cleaning job at growing sizes."""
import re
import time

import pandas as pd
from pyspark.sql import functions as F

from src.preprocessing.cleaner import clean
from src.preprocessing.spark_session import get_spark


def _pandas_clean(pdf: pd.DataFrame) -> pd.DataFrame:
    for c in ["title", "abstract", "objectives", "methodology"]:
        pdf[c] = pdf[c].fillna("").map(lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip())
    pdf = pdf[pdf["abstract"].str.len() >= 50]
    return pdf.drop_duplicates(subset=["title", "funder", "status"])


def run(base_pdf: pd.DataFrame, sizes=(1_000, 10_000, 100_000)) -> pd.DataFrame:
    spark = get_spark("benchmark")
    rows = []
    for n in sizes:
        big = pd.concat([base_pdf] * (n // len(base_pdf) + 1), ignore_index=True).head(n).copy()
        big["title"] = big["title"] + " " + big.index.astype(str)
        t = time.perf_counter(); _pandas_clean(big.copy()); tp = time.perf_counter() - t
        sdf = spark.createDataFrame(big)
        t = time.perf_counter(); clean(sdf).count(); ts = time.perf_counter() - t
        rows.append({"rows": n, "pandas_s": round(tp, 3), "spark_s": round(ts, 3)})
    return pd.DataFrame(rows)
