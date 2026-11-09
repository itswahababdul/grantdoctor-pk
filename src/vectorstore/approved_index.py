"""APPROVED library index (status == approved)."""
from src.vectorstore.base_index import VectorIndex


class ApprovedIndex(VectorIndex):
    name = "approved"
    STATUSES = ["approved"]
