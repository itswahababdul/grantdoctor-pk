"""Minimal cosine vector index (numpy). Swap for FAISS/Chroma later without touching other modules."""
import json
from pathlib import Path

import numpy as np
import pandas as pd


class VectorIndex:
    name = "base"

    def __init__(self):
        self.vectors = np.zeros((0, 1), dtype=np.float32)
        self.records: list[dict] = []

    def build_from_pandas(self, pdf: pd.DataFrame, vec_col: str = "embedding"):
        self.vectors = np.vstack([np.asarray(v, dtype=np.float32) for v in pdf[vec_col]]) if len(pdf) else self.vectors
        self.records = pdf.drop(columns=[vec_col]).to_dict("records")
        return self

    def search(self, qvec: np.ndarray, k: int = 5) -> list[tuple[int, float]]:
        if not len(self.records):
            return []
        scores = self.vectors @ np.asarray(qvec, dtype=np.float32)
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top]

    def save(self, directory: str):
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        np.save(d / "vectors.npy", self.vectors)
        with open(d / "records.json", "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, default=str)

    @classmethod
    def load(cls, directory: str):
        d = Path(directory)
        obj = cls()
        obj.vectors = np.load(d / "vectors.npy")
        with open(d / "records.json", encoding="utf-8") as f:
            obj.records = json.load(f)
        return obj
