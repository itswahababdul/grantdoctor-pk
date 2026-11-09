import shutil

import pytest

pytest.importorskip("pyspark")
if shutil.which("java") is None:
    pytest.skip("Java not installed", allow_module_level=True)

from src.preprocessing.chunker import chunk_dataframe
from src.preprocessing.cleaner import clean
from src.preprocessing.metadata_extractor import extract_budget, extract_duration_months
from src.preprocessing.spark_session import get_spark


def test_clean_and_chunk():
    spark = get_spark("test", "local[2]", 2)
    rows = [("P1", "T  one", "<b>" + "word " * 30 + "</b>", "obj", "meth", "HEC", "approved"),
            ("P2", "T one", "word " * 30, "obj", "meth", "HEC", "approved"),   # duplicate title
            ("P3", "Short", "tiny", "obj", "meth", "PSF", "approved")]        # too short
    df = spark.createDataFrame(rows, ["project_id", "title", "abstract", "objectives", "methodology", "funder", "status"])
    out = clean(df)
    assert out.count() == 1
    assert chunk_dataframe(out, 10, 2).count() >= 3


def test_regex_extractors():
    assert extract_budget("budget of PKR 5.2 million") == 5.2e6
    assert extract_duration_months("over 3 years") == 36
