"""Spark trend analytics across both libraries."""
from pyspark.sql import DataFrame, functions as F


def funding_by_year_funder(df: DataFrame) -> DataFrame:
    return (df.filter(F.col("status") == "approved")
            .groupBy("year", "funder")
            .agg(F.count("*").alias("projects"), F.sum("budget").alias("total_budget"))
            .orderBy("year", "funder"))


def approval_rate_by_field(df: DataFrame) -> DataFrame:
    """Only meaningful if rejected data is real/proxy. With synthetic negatives this is a demo metric."""
    return (df.groupBy("field")
            .agg(F.sum(F.when(F.col("status") == "approved", 1).otherwise(0)).alias("approved"),
                 F.sum(F.when(F.col("status") != "approved", 1).otherwise(0)).alias("not_approved"))
            .withColumn("approval_rate", F.round(F.col("approved") / (F.col("approved") + F.col("not_approved")), 3)))
