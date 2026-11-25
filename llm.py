"""
Optional LLM enrichment — the seam for a real model, kept OFF the demo path.

If OPENAI_API_KEY is set in the environment, `enrich()` rewrites a
locally-generated speech in a livelier advocate voice (grounded on the
same case facts — the model never sees anything else). If no key is set
(or the call fails), it returns the original text untouched, so the
hackathon demo always works offline with zero keys.

This mirrors the portfolio RAG pattern: local engine first, LLM as an
optional upgrade, never a hard dependency.
"""
from __future__ import annotations

import os


def enrich(text: str, speaker: str, case_statement: str) -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return text
    try:
        import urllib.request
        import json
        payload = json.dumps({
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [
                {"role": "system",
                 "content": "You are a courtroom advocate. Rewrite the speech "
                            "below in a sharper advocate voice. Do not invent "
                            "facts — use only the case statement given."},
                {"role": "user",
                 "content": f"Speaker: {speaker}\nCase: {case_statement}\n"
                            f"Speech to rewrite:\n{text}"},
            ],
            "temperature": 0.4,
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions", data=payload,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            out = json.loads(resp.read())
        return out["choices"][0]["message"]["content"].strip() or text
    except Exception:
        return text  # fail closed to the local engine
