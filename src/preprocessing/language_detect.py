"""Cheap Urdu/English detection by Unicode script ratio (no external model needed)."""
import re

from pyspark.sql import DataFrame, functions as F
from pyspark.sql.types import StringType

_ARABIC = re.compile(r"[\u0600-\u06FF]")
_LATIN = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> str:
    if not text:
        return "unknown"
    ar, la = len(_ARABIC.findall(text)), len(_LATIN.findall(text))
    if ar == 0 and la == 0:
        return "unknown"
    ratio = ar / (ar + la)
    return "ur" if ratio > 0.6 else ("mixed" if ratio > 0.1 else "en")


detect_language_udf = F.udf(detect_language, StringType())


def add_language(df: DataFrame) -> DataFrame:
    return df.withColumn("language", detect_language_udf(F.col("abstract")))
