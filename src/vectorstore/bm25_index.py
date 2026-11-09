"""Small dependency-free BM25 for the lexical half of hybrid retrieval."""
import math
import re
from collections import Counter


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", (text or "").lower())


class BM25Index:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tokens = [tokenize(d) for d in docs]
        self.N = len(docs)
        self.avgdl = (sum(len(t) for t in self.tokens) / self.N) if self.N else 0.0
        df = Counter()
        for t in self.tokens:
            df.update(set(t))
        self.idf = {w: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for w, n in df.items()}
        self.tf = [Counter(t) for t in self.tokens]

    def search(self, query: str, k: int = 5) -> list[tuple[int, float]]:
        q = tokenize(query)
        scores = []
        for i, tf in enumerate(self.tf):
            dl = len(self.tokens[i]) or 1
            s = 0.0
            for w in q:
                if w in tf:
                    f = tf[w]
                    s += self.idf.get(w, 0.0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
            scores.append(s)
        order = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [(i, scores[i]) for i in order if scores[i] > 0]
