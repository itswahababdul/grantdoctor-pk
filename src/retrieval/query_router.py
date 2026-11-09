"""Decide which library(ies) a question should search."""
REJECT_WORDS = ("reject", "declin", "not approved", "unapproved", "why not", "fail", "weak", "denied", "turned down")
APPROVE_WORDS = ("approved", "funded", "accepted", "success", "extend", "gap", "trend", "winning")


def route(query: str) -> list[str]:
    q = query.lower()
    rej = any(w in q for w in REJECT_WORDS)
    app = any(w in q for w in APPROVE_WORDS)
    if rej and not app:
        return ["rejected"]
    if app and not rej:
        return ["approved"]
    return ["approved", "rejected"]


PAPER_WORDS = ("paper", "iclr", "conference", "reviewer", "review comment", "peer review", "neural", "deep learning", "baseline")


def route_corpus(query: str) -> str:
    """Grant questions search HEC/PSF records; paper/reviewer questions search the PeerRead corpus."""
    q = query.lower()
    return "peer_review" if any(w in q for w in PAPER_WORDS) else "grant"
