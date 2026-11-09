"""Grounding guardrails: refuse without evidence, always attach citations."""
NO_CONTEXT = "I could not find supporting evidence in the approved/rejected libraries for this question."


def guard(answer: str, contexts: list[dict], min_score: float = 0.0) -> str:
    if not contexts:
        return NO_CONTEXT
    cited = {c["project_id"] for c in contexts if f"[{c['project_id']}]" in answer}
    if not cited:
        sources = ", ".join(sorted({c["project_id"] for c in contexts[:3]}))
        answer += f"\n\nSources: {sources}"
    return answer
