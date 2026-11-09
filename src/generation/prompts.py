SYSTEM = (
    "You are GrantDoctor-PK, an assistant that analyses HEC/PSF research proposals. "
    "Answer ONLY from the numbered context. Cite sources like [P-ID]. "
    "If the context does not contain the answer, say so clearly."
)


def build_prompt(question: str, contexts: list[dict]) -> str:
    ctx = "\n".join(
        f"[{c['project_id']}] ({c['library']}, {c.get('section','')}) {c['text']}" for c in contexts
    )
    return f"{SYSTEM}\n\nContext:\n{ctx}\n\nQuestion: {question}\nAnswer:"
