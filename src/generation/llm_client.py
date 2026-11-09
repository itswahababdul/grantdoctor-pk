"""Swappable LLM client. `extractive` works offline (returns best evidence); `ollama` uses a local model."""
import requests


class LLMClient:
    def __init__(self, provider: str = "extractive", model: str = "llama3.1", url: str = "http://localhost:11434/api/generate"):
        self.provider, self.model, self.url = provider, model, url

    def generate(self, prompt: str, contexts: list[dict]) -> str:
        if self.provider == "ollama":
            r = requests.post(self.url, json={"model": self.model, "prompt": prompt, "stream": False}, timeout=120)
            r.raise_for_status()
            return r.json().get("response", "").strip()
        # extractive fallback
        lines = [f"- [{c['project_id']}] ({c['library']}) {c['text'][:220]}" for c in contexts[:3]]
        return "Most relevant evidence found:\n" + "\n".join(lines)
