"""Fill missing budget / duration by regex over the text (e.g. 'PKR 5.2 million', '36 months')."""
import re

from pyspark.sql import DataFrame, functions as F
from pyspark.sql.types import DoubleType, IntegerType

_BUDGET = re.compile(r"(?:pkr|rs\.?)\s*([\d,.]+)\s*(million|m|billion|b|lakh|lac)?", re.I)
_MULT = {"million": 1e6, "m": 1e6, "billion": 1e9, "b": 1e9, "lakh": 1e5, "lac": 1e5}
_DUR = re.compile(r"(\d{1,3})\s*(months?|years?)", re.I)


def extract_budget(text: str):
    m = _BUDGET.search(text or "")
    if not m:
        return None
    try:
        val = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    return val * _MULT.get((m.group(2) or "").lower(), 1.0)


def extract_duration_months(text: str):
    m = _DUR.search(text or "")
    if not m:
        return None
    n = int(m.group(1))
    return n * 12 if m.group(2).lower().startswith("year") else n


_b = F.udf(extract_budget, DoubleType())
_d = F.udf(extract_duration_months, IntegerType())


def fill_metadata(df: DataFrame) -> DataFrame:
    blob = F.concat_ws(" ", "abstract", "methodology")
    return (
        df.withColumn("budget", F.coalesce("budget", _b(blob)))
        .withColumn("duration_months", F.coalesce("duration_months", _d(blob)))
    )
