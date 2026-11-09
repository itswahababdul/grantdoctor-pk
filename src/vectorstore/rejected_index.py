"""REJECTED library index (status in rejected / synthetic_rejected). Kept physically separate from approved."""
from src.vectorstore.base_index import VectorIndex


class RejectedIndex(VectorIndex):
    name = "rejected"
    STATUSES = ["rejected", "synthetic_rejected"]
