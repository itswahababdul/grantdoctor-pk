"""Section-aware word-window chunking. Pure function (unit-testable) + Spark wrapper."""
from pyspark.sql import DataFrame, functions as F
from pyspark.sql.types import ArrayType, IntegerType, StringType, StructField, StructType

SECTIONS = ["abstract", "objectives", "methodology", "reviews"]


def chunk_words(text: str, size: int = 120, overlap: int = 20) -> list[str]:
    words = (text or "").split()
    if not words:
        return []
    step = max(1, size - overlap)
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step) if words[i:i + size]]


def chunk_record(abstract, objectives, methodology, size=120, overlap=20, reviews=None):
    out = []
    for name, txt in zip(SECTIONS, [abstract, objectives, methodology, reviews]):
        for i, c in enumerate(chunk_words(txt, size, overlap)):
            out.append((name, i, c))
    return out


_schema = ArrayType(StructType([
    StructField("section", StringType()),
    StructField("chunk_idx", IntegerType()),
    StructField("text", StringType()),
]))


def chunk_dataframe(df: DataFrame, size: int = 120, overlap: int = 20) -> DataFrame:
    udf = F.udf(lambda a, o, m, r: chunk_record(a, o, m, size, overlap, r), _schema)
    out = df.withColumn("chunk", F.explode(udf("abstract", "objectives", "methodology", "review_text")))
    out = out.select(
        "*",
        F.col("chunk.section").alias("section"),
        F.col("chunk.chunk_idx").alias("chunk_idx"),
        F.col("chunk.text").alias("text"),
    ).drop("chunk")
    return out.withColumn("chunk_id", F.concat_ws("::", "project_id", "section", F.col("chunk_idx").cast("string")))
