"""
Real LLM layer for the Mini Courtroom.

Provider priority (first one that works wins):
  1. OpenAI — the provider Likhith chose on Oct 22, 2026. Set
     OPENAI_API_KEY (and optionally OPENAI_MODEL, OPENAI_BASE_URL for any
     OpenAI-compatible endpoint, e.g. Groq / OpenRouter). Keys live in
     env vars only — never in the repo, never in chat. The OpenAI key he
     pasted in chat on Oct 22 was treated as exposed and is NOT used.
  2. Pollinations — free public text API, no key needed, so the
     hackathon demo works out of the box. Used only when no key is set.
  3. None — every caller falls back to the local argument engine in
     courtroom.py, so a hearing always runs, online or offline.

`chat()` returns None (never raises) when the provider is unreachable,
so the courtroom can fail closed to the local engine speech-by-speech.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

TIMEOUT = 30


class LLMClient:
    def __init__(self, provider: str, model: str,
                 api_key: str = "", base_url: str = ""):
        self.provider = provider          # "openai" | "pollinations"
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def __repr__(self):  # never print the key
        return f"LLMClient(provider={self.provider!r}, model={self.model!r})"

    # -- OpenAI-compatible chat completions --------------------------
    def _openai_chat(self, system: str, user: str,
                     max_tokens: int) -> str | None:
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=payload,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                out = json.loads(resp.read())
            text = out["choices"][0]["message"]["content"].strip()
            return text or None
        except Exception:
            return None

    # -- Pollinations free API (no key) ------------------------------
    def _pollinations_chat(self, system: str, user: str,
                           max_tokens: int) -> str | None:
        payload = json.dumps({
            "model": "openai",
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }).encode()
        req = urllib.request.Request(
            "https://text.pollinations.ai/", data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                text = resp.read().decode().strip()
            return text or None
        except Exception:
            pass
        # GET fallback: the whole prompt in the URL path.
        prompt = f"{system}\n\n{user}"
        url = ("https://text.pollinations.ai/"
               + urllib.parse.quote(prompt) + "?model=openai")
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
                text = resp.read().decode().strip()
            return text or None
        except Exception:
            return None

    def chat(self, system: str, user: str, max_tokens: int = 420) -> str | None:
        if self.provider == "openai":
            return self._openai_chat(system, user, max_tokens)
        return self._pollinations_chat(system, user, max_tokens)


def get_client() -> LLMClient:
    """OpenAI when a key is set, otherwise the free no-key provider."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return LLMClient(
            provider="openai",
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=key,
            base_url=os.environ.get("OPENAI_BASE_URL",
                                    "https://api.openai.com/v1"))
    return LLMClient(provider="pollinations", model="openai")


def enrich(text: str, speaker: str, case_statement: str) -> str:
    """Backwards-compatible helper: rewrite one speech with the LLM,
    or return it untouched when the LLM is unavailable."""
    out = get_client().chat(
        "You are a courtroom advocate. Rewrite the speech below in a "
        "sharper advocate voice. Do not invent facts — use only the case "
        "statement given.",
        f"Speaker: {speaker}\nCase: {case_statement}\nSpeech:\n{text}")
    return out or text
