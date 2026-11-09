"""Distributed batch embedding with Spark `mapInPandas`."""
from pyspark.sql import DataFrame
from pyspark.sql.types import ArrayType, FloatType, StructField, StructType

from src.embeddings.embedder import get_embedder


def embed_dataframe(df: DataFrame, model_name: str = "hashing", text_col: str = "text") -> DataFrame:
    schema = StructType(df.schema.fields + [StructField("embedding", ArrayType(FloatType()))])

    def _embed_partition(batches):
        emb = get_embedder(model_name)  # created once per partition
        for pdf in batches:
            if len(pdf):
                pdf["embedding"] = [v.tolist() for v in emb.embed(pdf[text_col].tolist())]
            else:
                pdf["embedding"] = []
            yield pdf

    return df.mapInPandas(_embed_partition, schema)
