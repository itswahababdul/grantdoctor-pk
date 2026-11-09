"""Embedders. `hashing` = deterministic/offline (tests, CI). Real runs: sentence-transformers multilingual model."""
import hashlib
import re

import numpy as np


class HashingEmbedder:
    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in re.findall(r"\w+", (t or "").lower()):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                out[i, h % self.dim] += 1.0 if (h >> 64) % 2 == 0 else -1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


class SentenceTransformerEmbedder:
    def __init__(self, name: str):
        from sentence_transformers import SentenceTransformer  # optional dependency
        self.model = SentenceTransformer(name)

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def get_embedder(name: str = "hashing"):
    return HashingEmbedder() if name == "hashing" else SentenceTransformerEmbedder(name)
