"""One place to create the SparkSession (every Spark module imports this)."""
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession

ROOT = str(Path(__file__).resolve().parents[2])


def get_spark(app_name: str = "GrantDoctor-PK", master: str = "local[*]", shuffle_partitions: int = 8) -> SparkSession:
    # Workers must be able to `import src...` (needed for UDFs / mapInPandas).
    os.environ["PYTHONPATH"] = ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    return (
        SparkSession.builder.appName(app_name)
        .master(master)
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
